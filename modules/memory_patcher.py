"""
Memory Patcher Module
Runtime memory patching for Unity FPS unlock.
Scans the running game process and patches the frame rate cap value.

WARNING: This modifies game memory at runtime. Anti-cheat may detect this.
Use at your own risk.
"""

import ctypes
import ctypes.wintypes
import struct
import subprocess
from dataclasses import dataclass
from typing import Optional, Callable


# ─── Windows API Constants ───────────────────────────────────────────────────
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_ACCESS = PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_VM_OPERATION | PROCESS_QUERY_INFORMATION

MEM_COMMIT = 0x1000
PAGE_READWRITE = 0x04
PAGE_READONLY = 0x02
PAGE_EXECUTE_READ = 0x20
PAGE_EXECUTE_READWRITE = 0x40
PAGE_WRITECOPY = 0x08
PAGE_EXECUTE_WRITECOPY = 0x80

READABLE_PAGES = (PAGE_READWRITE, PAGE_READONLY, PAGE_EXECUTE_READ,
                  PAGE_EXECUTE_READWRITE, PAGE_WRITECOPY, PAGE_EXECUTE_WRITECOPY)

TH32CS_SNAPPROCESS = 0x00000002
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010

INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


# ─── Windows API Structures ──────────────────────────────────────────────────
class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ('dwSize', ctypes.c_uint),
        ('cntUsage', ctypes.c_uint),
        ('th32ProcessID', ctypes.c_uint),
        ('th32DefaultHeapID', ctypes.c_size_t),
        ('th32ModuleID', ctypes.c_uint),
        ('cntThreads', ctypes.c_uint),
        ('th32ParentProcessID', ctypes.c_uint),
        ('pcPriClassBase', ctypes.c_long),
        ('dwFlags', ctypes.c_uint),
        ('szExeFile', ctypes.c_wchar * 260),
    ]


class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [
        ('dwSize', ctypes.c_uint),
        ('th32ModuleID', ctypes.c_uint),
        ('th32ProcessID', ctypes.c_uint),
        ('GlbcntUsage', ctypes.c_uint),
        ('ProccntUsage', ctypes.c_uint),
        ('modBaseAddr', ctypes.c_void_p),
        ('modBaseSize', ctypes.c_uint),
        ('hModule', ctypes.c_void_p),
        ('szModule', ctypes.c_wchar * 256),
        ('szExePath', ctypes.c_wchar * 260),
    ]


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ('BaseAddress', ctypes.c_void_p),
        ('AllocationBase', ctypes.c_void_p),
        ('AllocationProtect', ctypes.c_uint),
        ('RegionSize', ctypes.c_size_t),
        ('State', ctypes.c_uint),
        ('Protect', ctypes.c_uint),
        ('Type', ctypes.c_uint),
    ]


# ─── Kernel32 Setup ─────────────────────────────────────────────────────────
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

kernel32.OpenProcess.argtypes = [ctypes.c_uint, ctypes.c_bool, ctypes.c_uint]
kernel32.OpenProcess.restype = ctypes.c_void_p

kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
kernel32.CloseHandle.restype = ctypes.c_bool

kernel32.ReadProcessMemory.argtypes = [
    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
    ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)
]
kernel32.ReadProcessMemory.restype = ctypes.c_bool

kernel32.WriteProcessMemory.argtypes = [
    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
    ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)
]
kernel32.WriteProcessMemory.restype = ctypes.c_bool

kernel32.VirtualQueryEx.argtypes = [
    ctypes.c_void_p, ctypes.c_void_p,
    ctypes.POINTER(MEMORY_BASIC_INFORMATION), ctypes.c_size_t
]
kernel32.VirtualQueryEx.restype = ctypes.c_size_t

kernel32.VirtualProtectEx.argtypes = [
    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
    ctypes.c_uint, ctypes.POINTER(ctypes.c_uint)
]
kernel32.VirtualProtectEx.restype = ctypes.c_bool

kernel32.CreateToolhelp32Snapshot.argtypes = [ctypes.c_uint, ctypes.c_uint]
kernel32.CreateToolhelp32Snapshot.restype = ctypes.c_void_p

kernel32.Process32FirstW.argtypes = [ctypes.c_void_p, ctypes.POINTER(PROCESSENTRY32W)]
kernel32.Process32FirstW.restype = ctypes.c_bool

kernel32.Process32NextW.argtypes = [ctypes.c_void_p, ctypes.POINTER(PROCESSENTRY32W)]
kernel32.Process32NextW.restype = ctypes.c_bool

kernel32.Module32FirstW.argtypes = [ctypes.c_void_p, ctypes.POINTER(MODULEENTRY32W)]
kernel32.Module32FirstW.restype = ctypes.c_bool

kernel32.Module32NextW.argtypes = [ctypes.c_void_p, ctypes.POINTER(MODULEENTRY32W)]
kernel32.Module32NextW.restype = ctypes.c_bool


# ─── Data Classes ────────────────────────────────────────────────────────────
@dataclass
class PatchResult:
    """Result of a memory patching operation."""
    success: bool
    message: str
    addresses_found: int = 0
    addresses_patched: int = 0


# ─── Memory Patcher ─────────────────────────────────────────────────────────
class MemoryPatcher:
    """Runtime memory patcher for Unity FPS unlock."""

    TARGET_PROCESS = "SCPSL.exe"
    # Modules to scan for the frame rate cap value
    TARGET_MODULES = ["UnityPlayer.dll", "GameAssembly.dll"]
    # The value we're looking for (60 FPS cap)
    SEARCH_VALUE = 60
    # VSync count value often found near targetFrameRate
    VSYNC_VALUE = 1
    # Chunk size for reading process memory
    CHUNK_SIZE = 65536  # 64 KB

    def __init__(self, log_callback: Optional[Callable[[str], None]] = None):
        self._log_callback = log_callback

    def _log(self, msg: str):
        """Log a message via the callback if available."""
        if self._log_callback:
            self._log_callback(msg)

    def is_game_running(self) -> bool:
        """Check if the target game process is currently running."""
        return self.find_process() is not None

    def find_process(self) -> Optional[int]:
        """Find the target process and return its PID."""
        # Use tasklist as a reliable fallback
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq {self.TARGET_PROCESS}",
                 "/FO", "CSV", "/NH"],
                capture_output=True, text=True, timeout=5,
                creationflags=0x08000000,  # CREATE_NO_WINDOW
                encoding="utf-8", errors="replace"
            )
            if result.returncode == 0:
                for line in result.stdout.strip().splitlines():
                    if self.TARGET_PROCESS.lower() in line.lower():
                        parts = line.replace('"', '').split(',')
                        if len(parts) >= 2:
                            try:
                                return int(parts[1])
                            except ValueError:
                                continue
        except Exception:
            pass

        # ctypes approach
        try:
            snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
            if snapshot == INVALID_HANDLE_VALUE:
                return None

            pe = PROCESSENTRY32W()
            pe.dwSize = ctypes.sizeof(PROCESSENTRY32W)

            if kernel32.Process32FirstW(snapshot, ctypes.byref(pe)):
                while True:
                    if pe.szExeFile.lower() == self.TARGET_PROCESS.lower():
                        pid = pe.th32ProcessID
                        kernel32.CloseHandle(snapshot)
                        return pid
                    if not kernel32.Process32NextW(snapshot, ctypes.byref(pe)):
                        break

            kernel32.CloseHandle(snapshot)
        except Exception:
            pass

        return None

    def get_module_info(self, pid: int, module_name: str) -> Optional[tuple[int, int]]:
        """Get base address and size of a module in the target process.
        
        Returns:
            Tuple of (base_address, size) or None if not found.
        """
        try:
            snapshot = kernel32.CreateToolhelp32Snapshot(
                TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
            if snapshot == INVALID_HANDLE_VALUE:
                self._log(f"  Failed to create module snapshot for PID {pid}")
                return None

            me = MODULEENTRY32W()
            me.dwSize = ctypes.sizeof(MODULEENTRY32W)

            if kernel32.Module32FirstW(snapshot, ctypes.byref(me)):
                while True:
                    if me.szModule.lower() == module_name.lower():
                        base = me.modBaseAddr
                        size = me.modBaseSize
                        kernel32.CloseHandle(snapshot)
                        return (base, size)
                    if not kernel32.Module32NextW(snapshot, ctypes.byref(me)):
                        break

            kernel32.CloseHandle(snapshot)
        except Exception as e:
            self._log(f"  Error enumerating modules: {e}")

        return None

    def read_memory(self, handle: int, address: int, size: int) -> Optional[bytes]:
        """Read memory from the target process."""
        buffer = ctypes.create_string_buffer(size)
        bytes_read = ctypes.c_size_t(0)

        success = kernel32.ReadProcessMemory(
            handle, ctypes.c_void_p(address), buffer,
            size, ctypes.byref(bytes_read)
        )

        if success and bytes_read.value > 0:
            return buffer.raw[:bytes_read.value]
        return None

    def write_memory(self, handle: int, address: int, data: bytes) -> bool:
        """Write memory to the target process."""
        # Try to make the page writable first
        old_protect = ctypes.c_uint(0)
        kernel32.VirtualProtectEx(
            handle, ctypes.c_void_p(address), len(data),
            PAGE_READWRITE, ctypes.byref(old_protect)
        )

        buffer = ctypes.create_string_buffer(data)
        bytes_written = ctypes.c_size_t(0)

        success = kernel32.WriteProcessMemory(
            handle, ctypes.c_void_p(address), buffer,
            len(data), ctypes.byref(bytes_written)
        )

        # Restore original protection
        if old_protect.value != 0:
            kernel32.VirtualProtectEx(
                handle, ctypes.c_void_p(address), len(data),
                old_protect.value, ctypes.byref(old_protect)
            )

        return bool(success) and bytes_written.value == len(data)

    def scan_module_for_value(self, handle: int, base: int, size: int,
                              value: int, value_size: int = 4) -> list[int]:
        """Scan a module's memory region for a specific integer value.
        
        Returns:
            List of addresses where the value was found.
        """
        target_bytes = struct.pack('<i', value)
        found_addresses = []
        offset = 0
        scan_count = 0

        while offset < size:
            chunk_size = min(self.CHUNK_SIZE, size - offset)
            data = self.read_memory(handle, base + offset, chunk_size)

            if data:
                # Search for the target value in this chunk
                pos = 0
                while True:
                    idx = data.find(target_bytes, pos)
                    if idx == -1:
                        break
                    # Only consider 4-byte aligned addresses
                    abs_addr = base + offset + idx
                    if abs_addr % 4 == 0:
                        found_addresses.append(abs_addr)
                    pos = idx + 1

            offset += chunk_size
            scan_count += 1

        return found_addresses

    def _score_candidate(self, handle: int, addr: int) -> int:
        """Score a candidate address based on surrounding context.
        
        Higher score = more likely to be the actual targetFrameRate value.
        Heuristics:
        - VSync count (1) nearby → +10
        - Other common quality values nearby → +5
        - Value is in a data section (not code) → +3
        """
        score = 0

        # Read surrounding memory (128 bytes before and after)
        context_data = self.read_memory(handle, addr - 128, 256 + 4)
        if not context_data:
            return 0

        # Look for vSyncCount value (1) as a 4-byte int nearby
        vsync_bytes = struct.pack('<i', self.VSYNC_VALUE)
        if vsync_bytes in context_data:
            score += 10

        # Look for common quality-related values
        # -1 (unlimited fps marker) as int
        neg_one = struct.pack('<i', -1)
        if neg_one in context_data:
            score += 3

        # Look for 0 values (common in settings structures)
        zero_bytes = struct.pack('<i', 0)
        zero_count = context_data.count(zero_bytes)
        if 2 <= zero_count <= 20:
            score += 2

        # Check that the surrounding area doesn't look like code
        # (x86 code tends to have more varied byte values)
        surrounding = context_data[:128] + context_data[132:]
        unique_bytes = len(set(surrounding))
        if unique_bytes < 100:  # Data sections tend to have less variety
            score += 3

        return score

    def unlock_fps(self, target_fps: int = -1) -> PatchResult:
        """Scan for and patch the FPS cap value in the running game.
        
        Args:
            target_fps: The target FPS to set. -1 for unlimited.
            
        Returns:
            PatchResult with success status and details.
        """
        # Step 1: Find the game process
        self._log("Step 1: Finding SCPSL.exe process...")
        pid = self.find_process()
        if pid is None:
            return PatchResult(False, "SCPSL.exe process not found. Is the game running?")
        self._log(f"  Found SCPSL.exe (PID: {pid})")

        # Step 2: Open the process
        self._log("Step 2: Opening process...")
        handle = kernel32.OpenProcess(PROCESS_ACCESS, False, pid)
        if not handle:
            error = ctypes.get_last_error()
            return PatchResult(
                False,
                f"Failed to open process (Error: {error}). "
                "Try running as Administrator."
            )
        self._log("  Process opened successfully")

        try:
            total_found = 0
            total_patched = 0
            best_candidates: list[tuple[int, int, str]] = []  # (address, score, module)

            # Step 3: Scan each target module
            for module_name in self.TARGET_MODULES:
                self._log(f"Step 3: Scanning {module_name}...")
                module_info = self.get_module_info(pid, module_name)

                if module_info is None:
                    self._log(f"  {module_name} not found in process, skipping")
                    continue

                base, size = module_info
                self._log(f"  {module_name}: base=0x{base:X}, size={size / 1024 / 1024:.1f} MB")

                # Scan for the value 60
                self._log(f"  Scanning for value {self.SEARCH_VALUE}...")
                addresses = self.scan_module_for_value(handle, base, size, self.SEARCH_VALUE)
                self._log(f"  Found {len(addresses)} occurrences of {self.SEARCH_VALUE}")
                total_found += len(addresses)

                # Score each candidate
                self._log("  Scoring candidates...")
                for addr in addresses:
                    score = self._score_candidate(handle, addr)
                    if score >= 5:  # Only consider reasonably scored candidates
                        best_candidates.append((addr, score, module_name))

            if not best_candidates:
                # Fallback: try broader memory scan if module scan found nothing good
                self._log("  No high-confidence candidates found in modules")
                self._log("  Attempting broader scan of UnityPlayer.dll with lower threshold...")

                module_info = self.get_module_info(pid, "UnityPlayer.dll")
                if module_info:
                    base, size = module_info
                    addresses = self.scan_module_for_value(handle, base, size, self.SEARCH_VALUE)
                    for addr in addresses:
                        score = self._score_candidate(handle, addr)
                        if score >= 2:
                            best_candidates.append((addr, score, "UnityPlayer.dll"))

            if not best_candidates:
                return PatchResult(
                    False,
                    f"Could not find FPS cap value in game memory. "
                    f"Total occurrences of {self.SEARCH_VALUE}: {total_found}, "
                    f"but none matched the expected pattern.",
                    addresses_found=total_found
                )

            # Sort by score (highest first)
            best_candidates.sort(key=lambda x: x[1], reverse=True)

            # Step 4: Patch the top candidates
            target_bytes = struct.pack('<i', target_fps)
            fps_label = "Unlimited" if target_fps < 0 else str(target_fps)
            max_patches = min(5, len(best_candidates))  # Patch top 5 at most

            self._log(f"Step 4: Patching top {max_patches} candidates to {fps_label}...")

            for i, (addr, score, module) in enumerate(best_candidates[:max_patches]):
                self._log(f"  Patching 0x{addr:X} (score: {score}, module: {module})...")
                if self.write_memory(handle, addr, target_bytes):
                    total_patched += 1
                    self._log(f"    ✅ Patched successfully")
                else:
                    self._log(f"    ❌ Failed to write")

            if total_patched > 0:
                return PatchResult(
                    True,
                    f"FPS patched to {fps_label}! "
                    f"({total_patched}/{max_patches} addresses patched)",
                    addresses_found=total_found,
                    addresses_patched=total_patched
                )
            else:
                return PatchResult(
                    False,
                    "Found candidates but failed to write to memory. "
                    "Try running as Administrator.",
                    addresses_found=total_found
                )

        finally:
            kernel32.CloseHandle(handle)
            self._log("  Process handle closed")
