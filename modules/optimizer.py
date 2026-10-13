"""
System Optimizer Module
Applies Windows, NVIDIA, and Unity-level performance optimizations
to maximize FPS in SCP: Secret Laboratory.
"""

import winreg
import subprocess
import os
import json
import ctypes
from dataclasses import dataclass
from typing import Optional, Callable


@dataclass
class OptResult:
    """Result of an optimization operation."""
    success: bool
    message: str
    category: str = ""


class SystemOptimizer:
    """Applies system-wide and game-specific performance optimizations."""

    GAME_EXE = "SCPSL.exe"
    DATA_DIR = "SCPSL_Data"
    BACKUP_FILE = ".optimizer_backup.json"

    def __init__(self, game_path: str, log_callback: Optional[Callable[[str], None]] = None):
        self.game_path = game_path
        self.backup_path = os.path.join(game_path, self.BACKUP_FILE)
        self.backup_data = self._load_backup()
        self._log_callback = log_callback

    def _log(self, msg: str):
        if self._log_callback:
            self._log_callback(msg)

    def _load_backup(self) -> dict:
        if os.path.isfile(self.backup_path):
            try:
                with open(self.backup_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {}

    def _save_backup(self):
        try:
            with open(self.backup_path, "w", encoding="utf-8") as f:
                json.dump(self.backup_data, f, indent=2)
        except IOError:
            pass

    # ── NVIDIA Optimizations ─────────────────────────────────────────────

    def optimize_nvidia_profile(self) -> OptResult:
        """Apply optimal NVIDIA Control Panel settings for SCP:SL via registry."""
        try:
            # Use nvidia-smi to set power mode and other settings
            commands = [
                # Prefer Maximum Performance
                ["nvidia-smi", "--power-limit", "300"],
                # Set persistence mode (keeps GPU initialized)
                ["nvidia-smi", "-pm", "1"],
            ]

            success_count = 0
            for cmd in commands:
                try:
                    result = subprocess.run(
                        cmd, capture_output=True, text=True, timeout=5,
                        creationflags=0x08000000, encoding="utf-8", errors="replace"
                    )
                    if result.returncode == 0:
                        success_count += 1
                except Exception:
                    pass

            # Set NVIDIA global settings via registry
            nv_settings_applied = self._apply_nvidia_registry_settings()

            return OptResult(
                True,
                f"NVIDIA optimizations applied (driver: {success_count} settings, "
                f"registry: {nv_settings_applied} settings)",
                "nvidia"
            )
        except Exception as e:
            return OptResult(False, f"NVIDIA optimization error: {e}", "nvidia")

    def _apply_nvidia_registry_settings(self) -> int:
        """Apply NVIDIA performance settings via registry."""
        count = 0
        try:
            # Set global NVIDIA 3D settings
            nv_path = r"SOFTWARE\NVIDIA Corporation\Global\NVTweak"
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, nv_path,
                                     0, winreg.KEY_SET_VALUE)
                # Threaded optimization
                winreg.SetValueEx(key, "Threaded optimization", 0, winreg.REG_DWORD, 1)
                count += 1
                winreg.CloseKey(key)
            except (PermissionError, FileNotFoundError, OSError):
                pass

        except Exception:
            pass
        return count

    # ── Windows Gaming Optimizations ─────────────────────────────────────

    def optimize_windows_gaming(self) -> OptResult:
        """Apply Windows gaming performance optimizations."""
        results = []

        # 1. Enable Hardware-Accelerated GPU Scheduling (HAGS)
        results.append(self._set_hags(True))

        # 2. Disable fullscreen optimizations for SCPSL.exe
        results.append(self._disable_fullscreen_optimizations())

        # 3. Optimize Game Mode settings
        results.append(self._optimize_game_mode())

        # 4. Disable Windows visual effects for performance
        results.append(self._optimize_visual_effects())

        # 5. Set multimedia timer resolution
        results.append(self._optimize_timer_resolution())

        # 6. Disable Nagle's algorithm for lower latency
        results.append(self._disable_nagle())

        success = sum(1 for r in results if r)
        return OptResult(
            success > 0,
            f"Windows gaming optimizations: {success}/{len(results)} applied",
            "windows"
        )

    def _set_hags(self, enable: bool) -> bool:
        """Enable/disable Hardware-Accelerated GPU Scheduling."""
        try:
            key_path = r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers"
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path,
                                 0, winreg.KEY_READ | winreg.KEY_SET_VALUE)
            
            # Backup
            try:
                original, _ = winreg.QueryValueEx(key, "HwSchMode")
                if "hags" not in self.backup_data:
                    self.backup_data["hags"] = original
                    self._save_backup()
            except FileNotFoundError:
                if "hags" not in self.backup_data:
                    self.backup_data["hags"] = 1  # default
                    self._save_backup()

            # 2 = enabled, 1 = disabled
            winreg.SetValueEx(key, "HwSchMode", 0, winreg.REG_DWORD, 2 if enable else 1)
            winreg.CloseKey(key)
            self._log(f"  HAGS: {'Enabled' if enable else 'Disabled'}")
            return True
        except (PermissionError, OSError) as e:
            self._log(f"  HAGS: Failed ({e})")
            return False

    def _disable_fullscreen_optimizations(self) -> bool:
        """Disable fullscreen optimizations for SCPSL.exe."""
        try:
            exe_path = os.path.join(self.game_path, self.GAME_EXE)
            # Set compatibility flags in registry
            reg_path = r"Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path,
                                 0, winreg.KEY_SET_VALUE | winreg.KEY_READ)

            # Backup existing value
            try:
                original, _ = winreg.QueryValueEx(key, exe_path)
                if "fullscreen_opt" not in self.backup_data:
                    self.backup_data["fullscreen_opt"] = {"path": exe_path, "value": original}
                    self._save_backup()
            except FileNotFoundError:
                if "fullscreen_opt" not in self.backup_data:
                    self.backup_data["fullscreen_opt"] = {"path": exe_path, "value": None}
                    self._save_backup()

            winreg.SetValueEx(key, exe_path, 0, winreg.REG_SZ,
                              "~ DISABLEDXMAXIMIZEDWINDOWEDMODE HIGHDPIAWARE")
            winreg.CloseKey(key)
            self._log("  Fullscreen optimizations: Disabled for SCPSL.exe")
            return True
        except (PermissionError, OSError) as e:
            self._log(f"  Fullscreen optimizations: Failed ({e})")
            return False

    def _optimize_game_mode(self) -> bool:
        """Optimize Windows Game Mode settings."""
        try:
            # Enable Game Mode
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                 r"Software\Microsoft\GameBar",
                                 0, winreg.KEY_SET_VALUE | winreg.KEY_READ)

            # Backup
            try:
                orig_auto = winreg.QueryValueEx(key, "AutoGameModeEnabled")[0]
                if "game_mode" not in self.backup_data:
                    self.backup_data["game_mode"] = {"AutoGameModeEnabled": orig_auto}
                    self._save_backup()
            except FileNotFoundError:
                pass

            winreg.SetValueEx(key, "AutoGameModeEnabled", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "AllowAutoGameMode", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
            self._log("  Game Mode: Enabled")
            return True
        except (PermissionError, OSError) as e:
            self._log(f"  Game Mode: Failed ({e})")
            return False

    def _optimize_visual_effects(self) -> bool:
        """Reduce Windows visual effects for better performance."""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                 r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects",
                                 0, winreg.KEY_SET_VALUE | winreg.KEY_READ)

            # Backup
            try:
                original, _ = winreg.QueryValueEx(key, "VisualFXSetting")
                if "visual_fx" not in self.backup_data:
                    self.backup_data["visual_fx"] = original
                    self._save_backup()
            except FileNotFoundError:
                if "visual_fx" not in self.backup_data:
                    self.backup_data["visual_fx"] = 0
                    self._save_backup()

            # 0 = Let Windows decide, 1 = Best appearance, 2 = Best performance, 3 = Custom
            winreg.SetValueEx(key, "VisualFXSetting", 0, winreg.REG_DWORD, 2)
            winreg.CloseKey(key)
            self._log("  Visual Effects: Set to Best Performance")
            return True
        except (PermissionError, OSError) as e:
            self._log(f"  Visual Effects: Failed ({e})")
            return False

    def _optimize_timer_resolution(self) -> bool:
        """Set Windows timer resolution for smoother frame pacing."""
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                 r"SYSTEM\CurrentControlSet\Control\Session Manager\kernel",
                                 0, winreg.KEY_SET_VALUE | winreg.KEY_READ)

            # Backup
            try:
                original, _ = winreg.QueryValueEx(key, "GlobalTimerResolutionRequests")
                if "timer_res" not in self.backup_data:
                    self.backup_data["timer_res"] = original
                    self._save_backup()
            except FileNotFoundError:
                if "timer_res" not in self.backup_data:
                    self.backup_data["timer_res"] = None
                    self._save_backup()

            winreg.SetValueEx(key, "GlobalTimerResolutionRequests", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
            self._log("  Timer Resolution: Optimized")
            return True
        except (PermissionError, OSError) as e:
            self._log(f"  Timer Resolution: Failed ({e})")
            return False

    def _disable_nagle(self) -> bool:
        """Disable Nagle's algorithm for lower network latency."""
        try:
            base_path = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces"
            base_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base_path)

            count = 0
            i = 0
            while True:
                try:
                    iface_name = winreg.EnumKey(base_key, i)
                    iface_path = f"{base_path}\\{iface_name}"
                    iface_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, iface_path,
                                               0, winreg.KEY_SET_VALUE | winreg.KEY_READ)

                    # Check if this interface has an IP address (active interface)
                    try:
                        ip, _ = winreg.QueryValueEx(iface_key, "DhcpIPAddress")
                        if ip and ip != "0.0.0.0":
                            winreg.SetValueEx(iface_key, "TcpAckFrequency", 0,
                                              winreg.REG_DWORD, 1)
                            winreg.SetValueEx(iface_key, "TCPNoDelay", 0,
                                              winreg.REG_DWORD, 1)
                            count += 1
                    except FileNotFoundError:
                        pass

                    winreg.CloseKey(iface_key)
                    i += 1
                except OSError:
                    break

            winreg.CloseKey(base_key)

            if "nagle" not in self.backup_data:
                self.backup_data["nagle"] = True
                self._save_backup()

            self._log(f"  Nagle's Algorithm: Disabled on {count} interface(s)")
            return count > 0
        except (PermissionError, OSError) as e:
            self._log(f"  Nagle's Algorithm: Failed ({e})")
            return False

    # ── Unity / Game Optimizations ───────────────────────────────────────

    def optimize_unity_config(self) -> OptResult:
        """Apply aggressive Unity boot.config optimizations."""
        boot_path = os.path.join(self.game_path, self.DATA_DIR, "boot.config")

        if not os.path.isfile(boot_path):
            return OptResult(False, "boot.config not found", "unity")

        try:
            with open(boot_path, "r", encoding="utf-8") as f:
                original = f.read()
                lines = original.splitlines()

            # Backup
            if "unity_boot" not in self.backup_data:
                self.backup_data["unity_boot"] = original
                self._save_backup()

            # Parse existing
            config = {}
            for line in lines:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, _, v = line.partition("=")
                    config[k.strip()] = v.strip()

            # Aggressive optimizations
            optimizations = {
                "gfx-enable-gfx-jobs": "1",
                "gfx-enable-native-gfx-jobs": "1",
                "gc-max-time-slice": "1",        # Minimize GC pauses
                "batch-mode": "0",
                "job-worker-count": "-1",         # Auto-detect optimal worker count
            }

            changes = 0
            for k, v in optimizations.items():
                if config.get(k) != v:
                    config[k] = v
                    changes += 1

            # Write
            new_lines = []
            written = set()
            for line in lines:
                stripped = line.strip()
                if "=" in stripped and not stripped.startswith("#"):
                    k = stripped.partition("=")[0].strip()
                    if k in config:
                        new_lines.append(f"{k}={config[k]}")
                        written.add(k)
                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)

            for k, v in config.items():
                if k not in written:
                    new_lines.append(f"{k}={v}")

            with open(boot_path, "w", encoding="utf-8") as f:
                f.write("\n".join(new_lines) + "\n")

            self._log(f"  Unity boot.config: {changes} optimizations applied")
            return OptResult(True,
                             f"Unity config optimized ({changes} changes)",
                             "unity")
        except PermissionError:
            return OptResult(False, "Permission denied. Run as Administrator.", "unity")
        except Exception as e:
            return OptResult(False, f"Unity config error: {e}", "unity")

    # ── Process Optimizations (Runtime) ──────────────────────────────────

    def optimize_running_process(self) -> OptResult:
        """Optimize the running game process (priority, affinity)."""
        try:
            # Find process
            result = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq {self.GAME_EXE}",
                 "/FO", "CSV", "/NH"],
                capture_output=True, text=True, timeout=5,
                creationflags=0x08000000, encoding="utf-8", errors="replace"
            )

            pid = None
            if result.returncode == 0:
                for line in result.stdout.strip().splitlines():
                    if self.GAME_EXE.lower() in line.lower():
                        parts = line.replace('"', '').split(',')
                        if len(parts) >= 2:
                            try:
                                pid = int(parts[1])
                            except ValueError:
                                continue

            if pid is None:
                return OptResult(False, "Game is not running", "process")

            optimizations_applied = []

            # Set High Priority
            try:
                result = subprocess.run(
                    ["wmic", "process", "where", f"ProcessId={pid}",
                     "CALL", "setpriority", "128"],  # 128 = High
                    capture_output=True, text=True, timeout=5,
                    creationflags=0x08000000, encoding="utf-8", errors="replace"
                )
                if result.returncode == 0:
                    optimizations_applied.append("High Priority")
                    self._log("  Process priority: High")
            except Exception:
                pass

            # Disable power throttling for the process
            try:
                exe_path = os.path.join(self.game_path, self.GAME_EXE)
                key_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options\SCPSL.exe\PerfOptions"
                try:
                    key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, key_path)
                    winreg.SetValueEx(key, "CpuPriorityClass", 0, winreg.REG_DWORD, 3)  # High
                    winreg.SetValueEx(key, "IoPriority", 0, winreg.REG_DWORD, 3)  # High
                    winreg.CloseKey(key)
                    optimizations_applied.append("CPU/IO Priority Boost")
                    self._log("  Persistent priority boost: Applied")

                    if "process_perf" not in self.backup_data:
                        self.backup_data["process_perf"] = True
                        self._save_backup()
                except PermissionError:
                    self._log("  Persistent priority: Needs admin")
            except Exception:
                pass

            if optimizations_applied:
                return OptResult(
                    True,
                    f"Process optimized: {', '.join(optimizations_applied)}",
                    "process"
                )
            else:
                return OptResult(False, "No process optimizations could be applied", "process")

        except Exception as e:
            return OptResult(False, f"Process optimization error: {e}", "process")

    # ── Power Plan ───────────────────────────────────────────────────────

    def set_ultimate_power_plan(self) -> OptResult:
        """Activate or create Ultimate Performance power plan."""
        try:
            # Try to activate Ultimate Performance plan
            # First, unhide it
            result = subprocess.run(
                ["powercfg", "-duplicatescheme", "e9a42b02-d5df-448d-aa00-03f14749eb61"],
                capture_output=True, text=True, timeout=5,
                creationflags=0x08000000, encoding="utf-8", errors="replace"
            )

            # Get the GUID of the created plan
            guid = None
            if result.returncode == 0 and result.stdout:
                # Output: "Power Scheme GUID: xxxx-xxxx  (Ultimate Performance)"
                output = result.stdout.strip()
                parts = output.split(":")
                if len(parts) >= 2:
                    guid_part = parts[-1].strip().split("(")[0].strip()
                    # Clean up GUID
                    guid = guid_part.strip()

            if not guid:
                # Try to find existing ultimate performance plan
                result = subprocess.run(
                    ["powercfg", "/list"],
                    capture_output=True, text=True, timeout=5,
                    creationflags=0x08000000, encoding="utf-8", errors="replace"
                )
                if result.returncode == 0:
                    for line in result.stdout.splitlines():
                        if "ultimate" in line.lower() or "e9a42b02" in line.lower():
                            # Extract GUID
                            parts = line.split(":")
                            if len(parts) >= 2:
                                guid = parts[1].strip().split("(")[0].strip().split()[0]
                                break

            if guid:
                # Backup current plan
                current = subprocess.run(
                    ["powercfg", "/getactivescheme"],
                    capture_output=True, text=True, timeout=5,
                    creationflags=0x08000000, encoding="utf-8", errors="replace"
                )
                if current.returncode == 0 and "power_plan" not in self.backup_data:
                    output = current.stdout.strip()
                    if ":" in output:
                        current_guid = output.split(":")[1].strip().split("(")[0].strip().split()[0]
                        self.backup_data["power_plan"] = current_guid
                        self._save_backup()

                # Activate Ultimate Performance
                result = subprocess.run(
                    ["powercfg", "/setactive", guid],
                    capture_output=True, text=True, timeout=5,
                    creationflags=0x08000000, encoding="utf-8", errors="replace"
                )
                if result.returncode == 0:
                    self._log("  Power Plan: Ultimate Performance activated")
                    return OptResult(True, "Ultimate Performance power plan activated", "power")

            return OptResult(False, "Could not set Ultimate Performance plan", "power")

        except Exception as e:
            return OptResult(False, f"Power plan error: {e}", "power")

    # ── Apply All ────────────────────────────────────────────────────────

    def apply_all_optimizations(self) -> list[OptResult]:
        """Apply all available optimizations."""
        results = []
        results.append(self.set_ultimate_power_plan())
        results.append(self.optimize_windows_gaming())
        results.append(self.optimize_unity_config())
        results.append(self.optimize_nvidia_profile())
        return results

    # ── Restore ──────────────────────────────────────────────────────────

    def restore_all(self) -> list[OptResult]:
        """Restore all optimized settings to defaults."""
        results = []

        # Restore power plan
        if "power_plan" in self.backup_data:
            try:
                guid = self.backup_data["power_plan"]
                subprocess.run(
                    ["powercfg", "/setactive", guid],
                    capture_output=True, timeout=5,
                    creationflags=0x08000000
                )
                del self.backup_data["power_plan"]
                results.append(OptResult(True, "Power plan restored", "power"))
            except Exception as e:
                results.append(OptResult(False, f"Power plan restore failed: {e}", "power"))

        # Restore HAGS
        if "hags" in self.backup_data:
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                     r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers",
                                     0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key, "HwSchMode", 0, winreg.REG_DWORD,
                                  self.backup_data["hags"])
                winreg.CloseKey(key)
                del self.backup_data["hags"]
                results.append(OptResult(True, "HAGS restored", "windows"))
            except Exception as e:
                results.append(OptResult(False, f"HAGS restore failed: {e}", "windows"))

        # Restore fullscreen optimizations
        if "fullscreen_opt" in self.backup_data:
            try:
                info = self.backup_data["fullscreen_opt"]
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                     r"Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers",
                                     0, winreg.KEY_SET_VALUE)
                if info["value"] is None:
                    try:
                        winreg.DeleteValue(key, info["path"])
                    except FileNotFoundError:
                        pass
                else:
                    winreg.SetValueEx(key, info["path"], 0, winreg.REG_SZ, info["value"])
                winreg.CloseKey(key)
                del self.backup_data["fullscreen_opt"]
                results.append(OptResult(True, "Fullscreen optimizations restored", "windows"))
            except Exception as e:
                results.append(OptResult(False, f"Fullscreen opt restore failed: {e}", "windows"))

        # Restore visual effects
        if "visual_fx" in self.backup_data:
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                     r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects",
                                     0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key, "VisualFXSetting", 0, winreg.REG_DWORD,
                                  self.backup_data["visual_fx"])
                winreg.CloseKey(key)
                del self.backup_data["visual_fx"]
                results.append(OptResult(True, "Visual effects restored", "windows"))
            except Exception as e:
                results.append(OptResult(False, f"Visual effects restore failed: {e}", "windows"))

        # Restore Unity boot config
        if "unity_boot" in self.backup_data:
            try:
                boot_path = os.path.join(self.game_path, self.DATA_DIR, "boot.config")
                with open(boot_path, "w", encoding="utf-8") as f:
                    f.write(self.backup_data["unity_boot"])
                del self.backup_data["unity_boot"]
                results.append(OptResult(True, "Unity boot.config restored", "unity"))
            except Exception as e:
                results.append(OptResult(False, f"Unity config restore failed: {e}", "unity"))

        # Restore process perf options
        if "process_perf" in self.backup_data:
            try:
                winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE,
                                 r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options\SCPSL.exe\PerfOptions")
                del self.backup_data["process_perf"]
                results.append(OptResult(True, "Process priority settings restored", "process"))
            except Exception as e:
                results.append(OptResult(False, f"Process restore failed: {e}", "process"))

        self._save_backup()

        if not results:
            results.append(OptResult(True, "Nothing to restore", ""))

        return results
