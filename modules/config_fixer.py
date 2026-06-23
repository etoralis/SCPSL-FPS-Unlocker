"""
Config Fixer Module
Applies safe, reversible configuration fixes to unlock FPS.
Handles boot.config, registry PlayerPrefs, and Windows GameDVR settings.
"""

import winreg
import shutil
import os
import json
import datetime
from dataclasses import dataclass
from typing import Optional


@dataclass
class FixResult:
    """Result of a fix operation."""
    success: bool
    message: str
    backup_path: Optional[str] = None


class ConfigFixer:
    """Applies and restores configuration fixes for SCP:SL FPS issues."""

    DATA_DIR = "SCPSL_Data"
    REG_PATH = r"Software\Northwood\SCPSL"
    GAMEDVR_REG_PATH = r"System\GameConfigStore"
    BACKUP_FILE = ".fps_unlocker_backup.json"

    def __init__(self, game_path: str):
        self.game_path = game_path
        self.backup_path = os.path.join(game_path, self.BACKUP_FILE)
        self.backup_data = self._load_backup()

    # ── Backup Management ────────────────────────────────────────────────

    def _load_backup(self) -> dict:
        """Load existing backup data if available."""
        if os.path.isfile(self.backup_path):
            try:
                with open(self.backup_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {}

    def _save_backup(self):
        """Save backup data to disk."""
        try:
            with open(self.backup_path, "w", encoding="utf-8") as f:
                json.dump(self.backup_data, f, indent=2)
        except IOError:
            pass

    # ── Boot Config ──────────────────────────────────────────────────────

    def fix_boot_config(self) -> FixResult:
        """Modify boot.config to optimize for higher FPS."""
        boot_path = os.path.join(self.game_path, self.DATA_DIR, "boot.config")

        if not os.path.isfile(boot_path):
            return FixResult(False, f"boot.config not found at {boot_path}")

        try:
            # Read current content
            with open(boot_path, "r", encoding="utf-8") as f:
                original_content = f.read()
                lines = original_content.splitlines()

            # Create timestamped backup
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"{boot_path}.{timestamp}.bak"
            shutil.copy2(boot_path, backup_file)

            # Store original in backup data
            if "boot_config" not in self.backup_data:
                self.backup_data["boot_config"] = {
                    "original_content": original_content,
                    "backup_file": backup_file,
                }
                self._save_backup()

            # Parse existing config
            config = {}
            for line in lines:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, _, value = line.partition("=")
                    config[key.strip()] = value.strip()

            # Apply optimizations (only add/modify, don't remove)
            optimizations = {
                "gfx-enable-native-gfx-jobs": "1",
                "gfx-enable-gfx-jobs": "1",
            }

            changes_made = []
            for key, value in optimizations.items():
                old_value = config.get(key)
                if old_value != value:
                    config[key] = value
                    if old_value is not None:
                        changes_made.append(f"{key}: {old_value} → {value}")
                    else:
                        changes_made.append(f"{key}: (added) {value}")

            # Write modified config
            new_lines = []
            written_keys = set()
            for line in lines:
                stripped = line.strip()
                if "=" in stripped and not stripped.startswith("#"):
                    key = stripped.partition("=")[0].strip()
                    if key in config:
                        new_lines.append(f"{key}={config[key]}")
                        written_keys.add(key)
                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)

            # Add new keys that weren't in the original file
            for key, value in config.items():
                if key not in written_keys:
                    new_lines.append(f"{key}={value}")

            with open(boot_path, "w", encoding="utf-8") as f:
                f.write("\n".join(new_lines) + "\n")

            if changes_made:
                return FixResult(True,
                                 f"boot.config optimized ({len(changes_made)} changes). "
                                 f"Backup: {os.path.basename(backup_file)}",
                                 backup_file)
            else:
                return FixResult(True, "boot.config already optimized, no changes needed")

        except PermissionError:
            return FixResult(False,
                             "Permission denied writing boot.config. Try running as Administrator.")
        except Exception as e:
            return FixResult(False, f"Error modifying boot.config: {e}")

    def restore_boot_config(self) -> FixResult:
        """Restore boot.config from backup."""
        boot_path = os.path.join(self.game_path, self.DATA_DIR, "boot.config")
        backup = self.backup_data.get("boot_config")

        if not backup:
            return FixResult(False, "No boot.config backup found")

        try:
            original = backup.get("original_content", "")
            if original:
                with open(boot_path, "w", encoding="utf-8") as f:
                    f.write(original)
                del self.backup_data["boot_config"]
                self._save_backup()
                return FixResult(True, "boot.config restored to original")
            else:
                return FixResult(False, "Backup data is empty")
        except Exception as e:
            return FixResult(False, f"Error restoring boot.config: {e}")

    # ── GameDVR ──────────────────────────────────────────────────────────

    def fix_game_dvr(self) -> FixResult:
        """Disable Windows GameDVR which can cap FPS to 60."""
        try:
            # Save original values
            original_values = {}
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.GAMEDVR_REG_PATH,
                                     0, winreg.KEY_READ)
                for name in ["GameDVR_Enabled", "GameDVR_FSEBehaviorMode",
                             "GameDVR_HonorUserFSEBehaviorMode",
                             "GameDVR_EFSEFeatureFlags",
                             "GameDVR_DXGIHonorFSEWindowsCompatible"]:
                    try:
                        value, reg_type = winreg.QueryValueEx(key, name)
                        original_values[name] = {"value": value, "type": reg_type}
                    except FileNotFoundError:
                        pass
                winreg.CloseKey(key)
            except (FileNotFoundError, OSError):
                pass

            # Store backup
            if "gamedvr" not in self.backup_data:
                self.backup_data["gamedvr"] = original_values
                self._save_backup()

            # Apply fixes
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.GAMEDVR_REG_PATH,
                                 0, winreg.KEY_SET_VALUE)

            winreg.SetValueEx(key, "GameDVR_Enabled", 0, winreg.REG_DWORD, 0)
            winreg.SetValueEx(key, "GameDVR_FSEBehaviorMode", 0, winreg.REG_DWORD, 2)
            winreg.SetValueEx(key, "GameDVR_HonorUserFSEBehaviorMode", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "GameDVR_EFSEFeatureFlags", 0, winreg.REG_DWORD, 0)
            winreg.SetValueEx(key, "GameDVR_DXGIHonorFSEWindowsCompatible", 0,
                              winreg.REG_DWORD, 1)

            winreg.CloseKey(key)

            return FixResult(True, "GameDVR disabled successfully")

        except PermissionError:
            return FixResult(False,
                             "Permission denied. Try running as Administrator.")
        except Exception as e:
            return FixResult(False, f"Error disabling GameDVR: {e}")

    def restore_game_dvr(self) -> FixResult:
        """Restore GameDVR settings to original values."""
        backup = self.backup_data.get("gamedvr")
        if not backup:
            return FixResult(False, "No GameDVR backup found")

        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.GAMEDVR_REG_PATH,
                                 0, winreg.KEY_SET_VALUE)

            for name, info in backup.items():
                winreg.SetValueEx(key, name, 0, info["type"], info["value"])

            winreg.CloseKey(key)

            del self.backup_data["gamedvr"]
            self._save_backup()
            return FixResult(True, "GameDVR settings restored")

        except Exception as e:
            return FixResult(False, f"Error restoring GameDVR: {e}")

    # ── Fullscreen Mode ──────────────────────────────────────────────────

    def fix_fullscreen_mode(self, mode: int = 0) -> FixResult:
        """Change the fullscreen mode in registry.
        
        Args:
            mode: 0=Exclusive Fullscreen, 1=Borderless, 2=Maximized, 3=Windowed
        """
        mode_names = {
            0: "Exclusive Fullscreen",
            1: "Borderless Fullscreen",
            2: "Maximized Window",
            3: "Windowed",
        }

        try:
            # Read current value
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.REG_PATH,
                                     0, winreg.KEY_READ)
                current, _ = winreg.QueryValueEx(
                    key, "Screenmanager Fullscreen mode_h3630240806")
                winreg.CloseKey(key)

                # Store backup
                if "fullscreen" not in self.backup_data:
                    self.backup_data["fullscreen"] = {"original_mode": current}
                    self._save_backup()
            except (FileNotFoundError, OSError):
                current = -1

            if current == mode:
                return FixResult(True,
                                 f"Already set to {mode_names.get(mode, 'Unknown')}")

            # Apply
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.REG_PATH,
                                 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "Screenmanager Fullscreen mode_h3630240806",
                              0, winreg.REG_DWORD, mode)
            winreg.SetValueEx(key, "Screenmanager Fullscreen mode Default_h401710285",
                              0, winreg.REG_DWORD, mode)
            winreg.CloseKey(key)

            return FixResult(
                True,
                f"Fullscreen mode changed: {mode_names.get(current, 'Unknown')} → "
                f"{mode_names.get(mode, 'Unknown')}")

        except PermissionError:
            return FixResult(False, "Permission denied. Try running as Administrator.")
        except Exception as e:
            return FixResult(False, f"Error changing fullscreen mode: {e}")

    def restore_fullscreen_mode(self) -> FixResult:
        """Restore fullscreen mode to original value."""
        backup = self.backup_data.get("fullscreen")
        if not backup:
            return FixResult(False, "No fullscreen mode backup found")

        try:
            original = backup.get("original_mode", 1)
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.REG_PATH,
                                 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "Screenmanager Fullscreen mode_h3630240806",
                              0, winreg.REG_DWORD, original)
            winreg.SetValueEx(key, "Screenmanager Fullscreen mode Default_h401710285",
                              0, winreg.REG_DWORD, original)
            winreg.CloseKey(key)

            del self.backup_data["fullscreen"]
            self._save_backup()

            modes = {0: "Exclusive", 1: "Borderless", 2: "Maximized", 3: "Windowed"}
            return FixResult(True,
                             f"Fullscreen mode restored to {modes.get(original, 'Unknown')}")

        except Exception as e:
            return FixResult(False, f"Error restoring fullscreen mode: {e}")

    # ── Steam Launch Options ─────────────────────────────────────────────

    def set_steam_launch_options_hint(self) -> str:
        """Return instructions for setting Steam launch options."""
        return (
            "To set Steam launch options:\n"
            "1. Open Steam\n"
            "2. Right-click SCP: Secret Laboratory\n"
            "3. Click Properties\n"
            "4. In Launch Options, add:\n"
            "   -screen-fullscreen 1 -window-mode exclusive\n"
        )

    # ── Batch Operations ─────────────────────────────────────────────────

    def apply_all_safe_fixes(self) -> list[FixResult]:
        """Apply all safe (config-based) fixes."""
        results = []
        results.append(self.fix_game_dvr())
        results.append(self.fix_boot_config())
        results.append(self.fix_fullscreen_mode(0))  # Exclusive fullscreen
        return results

    def restore_all(self) -> list[FixResult]:
        """Restore all backed-up settings."""
        results = []

        if "gamedvr" in self.backup_data:
            results.append(self.restore_game_dvr())

        if "boot_config" in self.backup_data:
            results.append(self.restore_boot_config())

        if "fullscreen" in self.backup_data:
            results.append(self.restore_fullscreen_mode())

        if not results:
            results.append(FixResult(True, "No backups to restore — nothing was changed"))

        return results
