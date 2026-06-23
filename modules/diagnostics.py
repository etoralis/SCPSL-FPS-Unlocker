"""
System Diagnostics Module
Gathers system, GPU, display, and game information for FPS troubleshooting.
"""

import ctypes
import ctypes.wintypes
import winreg
import subprocess
import os
import platform
from dataclasses import dataclass, field
from typing import Optional


# ─── Display Settings via ctypes ─────────────────────────────────────────────
class DEVMODEW(ctypes.Structure):
    """Win32 DEVMODEW structure for EnumDisplaySettingsW."""
    _fields_ = [
        ('dmDeviceName', ctypes.c_wchar * 32),
        ('dmSpecVersion', ctypes.c_ushort),
        ('dmDriverVersion', ctypes.c_ushort),
        ('dmSize', ctypes.c_ushort),
        ('dmDriverExtra', ctypes.c_ushort),
        ('dmFields', ctypes.c_uint),
        ('dmPositionX', ctypes.c_int),
        ('dmPositionY', ctypes.c_int),
        ('dmDisplayOrientation', ctypes.c_uint),
        ('dmDisplayFixedOutput', ctypes.c_uint),
        ('dmColor', ctypes.c_short),
        ('dmDuplex', ctypes.c_short),
        ('dmYResolution', ctypes.c_short),
        ('dmTTOption', ctypes.c_short),
        ('dmCollate', ctypes.c_short),
        ('dmFormName', ctypes.c_wchar * 32),
        ('dmLogPixels', ctypes.c_ushort),
        ('dmBitsPerPel', ctypes.c_uint),
        ('dmPelsWidth', ctypes.c_uint),
        ('dmPelsHeight', ctypes.c_uint),
        ('dmDisplayFlags', ctypes.c_uint),
        ('dmDisplayFrequency', ctypes.c_uint),
    ]


ENUM_CURRENT_SETTINGS = -1


# ─── Data Classes ────────────────────────────────────────────────────────────
@dataclass
class SystemInfo:
    """Container for all system diagnostic information."""
    gpu_name: str = "Unknown"
    gpu_driver: str = "Unknown"
    monitor_refresh_rate: int = 0
    monitor_resolution: str = "Unknown"
    power_plan: str = "Unknown"
    game_dvr_enabled: bool = False
    windows_version: str = "Unknown"
    fullscreen_mode: int = -1
    fullscreen_mode_name: str = "Unknown"
    game_path: Optional[str] = None
    is_il2cpp: bool = False
    has_anticheat: bool = False
    unity_version: str = "Unknown"
    boot_config: dict = field(default_factory=dict)
    registry_values: dict = field(default_factory=dict)


# ─── Diagnostics Class ──────────────────────────────────────────────────────
class SystemDiagnostics:
    """Gathers system and game diagnostics for FPS troubleshooting."""

    GAME_NAME = "SCP Secret Laboratory"
    GAME_EXE = "SCPSL.exe"
    DATA_DIR = "SCPSL_Data"
    REG_PATH = r"Software\Northwood\SCPSL"

    FULLSCREEN_MODES = {
        0: "Exclusive Fullscreen",
        1: "Borderless Fullscreen",
        2: "Maximized Window",
        3: "Windowed",
    }

    def get_full_diagnostics(self) -> SystemInfo:
        """Run all diagnostic checks and return a SystemInfo object."""
        info = SystemInfo()

        # Windows version
        info.windows_version = platform.version()

        # GPU
        info.gpu_name, info.gpu_driver = self.get_gpu_info()

        # Monitor
        info.monitor_refresh_rate, info.monitor_resolution = self.get_monitor_info()

        # Power plan
        info.power_plan = self.get_power_plan()

        # GameDVR
        info.game_dvr_enabled = self.check_game_dvr()

        # Game installation
        info.game_path = self.find_game_installation()

        if info.game_path:
            # Check IL2CPP
            ga_dll = os.path.join(info.game_path, "GameAssembly.dll")
            info.is_il2cpp = os.path.isfile(ga_dll)

            # Check anti-cheat
            slac_dll = os.path.join(info.game_path, "SL-AC.dll")
            info.has_anticheat = os.path.isfile(slac_dll)

            # Boot config
            info.boot_config = self.get_boot_config(info.game_path)

        # Registry
        info.registry_values = self.get_registry_values()

        # Fullscreen mode
        info.fullscreen_mode, info.fullscreen_mode_name = self.get_fullscreen_mode()

        return info

    def find_game_installation(self) -> Optional[str]:
        """Find SCP:SL installation by searching Steam library folders."""
        # Try to get Steam path from registry
        steam_path = self._get_steam_path()
        search_paths: list[str] = []

        if steam_path:
            # Parse libraryfolders.vdf to find all library paths
            vdf_path = os.path.join(steam_path, "steamapps", "libraryfolders.vdf")
            if os.path.isfile(vdf_path):
                try:
                    with open(vdf_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    # Simple VDF parser: find all "path" values
                    for line in content.splitlines():
                        line = line.strip()
                        if line.startswith('"path"'):
                            parts = line.split('"')
                            if len(parts) >= 4:
                                lib_path = parts[3].replace("\\\\", "\\")
                                game_dir = os.path.join(lib_path, "steamapps", "common",
                                                         self.GAME_NAME)
                                search_paths.append(game_dir)
                except Exception:
                    pass

            # Also add the main Steam library
            main_lib = os.path.join(steam_path, "steamapps", "common", self.GAME_NAME)
            if main_lib not in search_paths:
                search_paths.insert(0, main_lib)

        # Add common fallback paths
        fallbacks = [
            r"C:\Program Files (x86)\Steam\steamapps\common\SCP Secret Laboratory",
            r"C:\Program Files\Steam\steamapps\common\SCP Secret Laboratory",
            r"D:\Steam\steamapps\common\SCP Secret Laboratory",
            r"D:\SteamLibrary\steamapps\common\SCP Secret Laboratory",
            r"E:\SteamLibrary\steamapps\common\SCP Secret Laboratory",
            r"F:\SteamLibrary\steamapps\common\SCP Secret Laboratory",
        ]
        for fb in fallbacks:
            if fb not in search_paths:
                search_paths.append(fb)

        # Search for the game
        for path in search_paths:
            exe_path = os.path.join(path, self.GAME_EXE)
            if os.path.isfile(exe_path):
                return path

        return None

    def _get_steam_path(self) -> Optional[str]:
        """Get Steam installation path from registry."""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
            value, _ = winreg.QueryValueEx(key, "SteamPath")
            winreg.CloseKey(key)
            return str(value).replace("/", "\\")
        except (FileNotFoundError, OSError):
            return None

    def get_gpu_info(self) -> tuple[str, str]:
        """Get GPU name and driver version."""
        # Try nvidia-smi first
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=5,
                creationflags=0x08000000, encoding="utf-8", errors="replace"
            )
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split(",")
                if len(parts) >= 2:
                    return parts[0].strip(), parts[1].strip()
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            pass

        # Fallback to WMIC
        try:
            result = subprocess.run(
                ["wmic", "path", "win32_VideoController", "get",
                 "name,DriverVersion", "/format:csv"],
                capture_output=True, text=True, timeout=10,
                creationflags=0x08000000, encoding="utf-8", errors="replace"
            )
            if result.returncode == 0:
                lines = [l.strip() for l in result.stdout.strip().splitlines() if l.strip()]
                for line in lines[1:]:  # Skip header
                    parts = line.split(",")
                    if len(parts) >= 3:
                        driver = parts[1].strip()
                        name = parts[2].strip()
                        # Prefer discrete GPU
                        if any(kw in name.upper() for kw in ["NVIDIA", "RTX", "GTX", "RADEON", "RX"]):
                            return name, driver
                # Return first if no discrete GPU found
                if len(lines) > 1:
                    parts = lines[1].split(",")
                    if len(parts) >= 3:
                        return parts[2].strip(), parts[1].strip()
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            pass

        return "Unknown", "Unknown"

    def get_monitor_info(self) -> tuple[int, str]:
        """Get primary monitor refresh rate and resolution using Win32 API."""
        try:
            user32 = ctypes.windll.user32
            dm = DEVMODEW()
            dm.dmSize = ctypes.sizeof(DEVMODEW)

            if user32.EnumDisplaySettingsW(None, ENUM_CURRENT_SETTINGS, ctypes.byref(dm)):
                refresh = dm.dmDisplayFrequency
                width = dm.dmPelsWidth
                height = dm.dmPelsHeight
                if width > 0 and height > 0:
                    return refresh, f"{width}x{height}"
        except Exception:
            pass

        # Fallback: try WMIC
        try:
            result = subprocess.run(
                ["wmic", "path", "Win32_VideoController", "get",
                 "CurrentHorizontalResolution,CurrentVerticalResolution,CurrentRefreshRate",
                 "/format:csv"],
                capture_output=True, text=True, timeout=10,
                creationflags=0x08000000, encoding="utf-8", errors="replace"
            )
            if result.returncode == 0:
                lines = [l.strip() for l in result.stdout.strip().splitlines() if l.strip()]
                for line in lines[1:]:
                    parts = line.split(",")
                    if len(parts) >= 4:
                        try:
                            hr = int(parts[1]) if parts[1] else 0
                            rr = int(parts[2]) if parts[2] else 0
                            vr = int(parts[3]) if parts[3] else 0
                            if hr > 0 and vr > 0 and rr > 0:
                                return rr, f"{hr}x{vr}"
                        except ValueError:
                            continue
        except Exception:
            pass

        return 0, "Unknown"

    def get_power_plan(self) -> str:
        """Get the active Windows power plan name."""
        try:
            result = subprocess.run(
                ["powercfg", "/getactivescheme"],
                capture_output=True, text=True, timeout=5,
                creationflags=0x08000000, encoding="utf-8", errors="replace"
            )
            if result.returncode == 0:
                output = result.stdout.strip()
                # Format: "Power Scheme GUID: xxx  (Name)"
                if "(" in output and ")" in output:
                    name = output[output.index("(") + 1:output.rindex(")")]
                    return name
                return output
        except Exception:
            pass
        return "Unknown"

    def check_game_dvr(self) -> bool:
        """Check if Windows GameDVR is enabled."""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"System\GameConfigStore")
            value, _ = winreg.QueryValueEx(key, "GameDVR_Enabled")
            winreg.CloseKey(key)
            return bool(value)
        except (FileNotFoundError, OSError):
            return False

    def get_registry_values(self) -> dict:
        """Read all Unity PlayerPrefs from the SCP:SL registry key."""
        values = {}
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.REG_PATH)
            i = 0
            while True:
                try:
                    name, data, reg_type = winreg.EnumValue(key, i)
                    values[name] = {"value": data, "type": reg_type}
                    i += 1
                except OSError:
                    break
            winreg.CloseKey(key)
        except (FileNotFoundError, OSError):
            pass
        return values

    def get_boot_config(self, game_path: str) -> dict:
        """Parse the Unity boot.config file."""
        config = {}
        boot_path = os.path.join(game_path, self.DATA_DIR, "boot.config")
        if os.path.isfile(boot_path):
            try:
                with open(boot_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if "=" in line and not line.startswith("#"):
                            key, _, value = line.partition("=")
                            config[key.strip()] = value.strip()
            except Exception:
                pass
        return config

    def get_fullscreen_mode(self) -> tuple[int, str]:
        """Get the current fullscreen mode from registry."""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.REG_PATH)
            value, _ = winreg.QueryValueEx(key, "Screenmanager Fullscreen mode_h3630240806")
            winreg.CloseKey(key)
            mode = int(value)
            return mode, self.FULLSCREEN_MODES.get(mode, f"Unknown ({mode})")
        except (FileNotFoundError, OSError, ValueError):
            return -1, "Unknown"
