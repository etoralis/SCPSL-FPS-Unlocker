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
import threading
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

kernel32.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint)]
kernel32.GetExitCodeProcess.restype = ctypes.c_bool

STILL_ACTIVE = 259


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
    TARGET_MODULE = "UnityPlayer.dll"
    # Unity internal-call names used to locate the targetFrameRate global
    ICALL_GETTER = b"UnityEngine.Application::get_targetFrameRate"
    ICALL_SETTER = b"UnityEngine.Application::set_targetFrameRate"
    # Chunk size for reading process memory
    CHUNK_SIZE = 65536  # 64 KB
    # How often the keep-alive loop checks the value (seconds)
    KEEPALIVE_INTERVAL = 1.5

    def __init__(self, log_callback: Optional[Callable[[str], None]] = None):
        self._log_callback = log_callback
        # Cache: (pid, address) of the resolved targetFrameRate global
        self._cached_pid: Optional[int] = None
        self._cached_addr: Optional[int] = None
        self._keepalive_stop: Optional[threading.Event] = None
        self._keepalive_thread: Optional[threading.Thread] = None

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

    # ── Address resolution ──────────────────────────────────────────────

    def _read_module_image(self, handle: int, base: int, size: int) -> bytes:
        """Read a whole module image from the target process."""
        buf = bytearray(size)
        offset = 0
        while offset < size:
            chunk = min(self.CHUNK_SIZE, size - offset)
            data = self.read_memory(handle, base + offset, chunk)
            if data:
                buf[offset:offset + len(data)] = data
            offset += chunk
        return bytes(buf)

    @staticmethod
    def _decode_rip_access(image: bytes, func_off: int, opcode: int) -> Optional[int]:
        """Decode `opcode r32, [rip+rel32]` at func_off (following one jmp).

        Returns the module-relative offset of the referenced global, or None.
        opcode: 0x8B for the getter (mov eax,[rip+x]), 0x89 for the setter.
        """
        for _ in range(2):
            if func_off < 0 or func_off + 7 > len(image):
                return None
            b0 = image[func_off]
            if b0 == 0xE9:  # jmp rel32 -> follow
                rel = struct.unpack_from("<i", image, func_off + 1)[0]
                func_off = func_off + 5 + rel
                continue
            if b0 == opcode and (image[func_off + 1] & 0xC7) == 0x05:
                rel = struct.unpack_from("<i", image, func_off + 2)[0]
                return func_off + 6 + rel
            return None
        return None

    def _resolve_target_framerate(self, image: bytes, base: int) -> Optional[int]:
        """Find the absolute address of Unity's targetFrameRate global.

        Unity registers internal calls through two parallel tables inside
        UnityPlayer.dll: a null-terminated table of name pointers followed by
        a table of function pointers. The getter for targetFrameRate is a tiny
        `mov eax, [rip+X]; ret`, so decoding it gives the exact address.
        """
        size = len(image)
        name_off = image.find(self.ICALL_GETTER + b"\x00")
        if name_off == -1:
            self._log("  get_targetFrameRate icall name not found")
            return None

        # Find the 8-byte aligned pointer to the name string
        needle = struct.pack("<Q", base + name_off)
        entry = image.find(needle)
        while entry != -1 and entry % 8 != 0:
            entry = image.find(needle, entry + 1)
        if entry == -1:
            self._log("  icall name table not found")
            return None

        def qword(off: int) -> int:
            return struct.unpack_from("<Q", image, off)[0]

        def is_name_ptr(off: int) -> bool:
            if off < 0 or off + 8 > size:
                return False
            rel = qword(off) - base
            return 0 <= rel < size - 8 and image.startswith(b"Unity", rel)

        start = entry
        while is_name_ptr(start - 8):
            start -= 8
        end = entry
        while is_name_ptr(end):
            end += 8
        index = (entry - start) // 8

        # Function table follows the name table after its null terminator(s)
        func_table = end
        skipped = 0
        while func_table + 8 <= size and qword(func_table) == 0 and skipped < 4:
            func_table += 8
            skipped += 1

        candidates: list[int] = []
        getter = qword(func_table + index * 8) - base
        g = self._decode_rip_access(image, getter, 0x8B)
        if g is not None:
            candidates.append(g)

        # Cross-check with the setter if it is the next entry
        if is_name_ptr(end - 8) and index + 1 < (end - start) // 8:
            next_name = qword(entry + 8) - base
            if image.startswith(self.ICALL_SETTER + b"\x00", next_name):
                setter = qword(func_table + (index + 1) * 8) - base
                s = self._decode_rip_access(image, setter, 0x89)
                if s is not None:
                    if g is not None and s != g:
                        self._log("  Getter/setter disagree, using getter")
                    elif g is None:
                        candidates.append(s)

        for off in candidates:
            if 0 <= off < size:
                return base + off
        self._log("  Could not decode targetFrameRate accessor")
        return None

    def _get_address(self, handle: int, pid: int) -> Optional[int]:
        """Return the cached or freshly resolved targetFrameRate address."""
        if self._cached_pid == pid and self._cached_addr:
            return self._cached_addr
        module_info = self.get_module_info(pid, self.TARGET_MODULE)
        if module_info is None:
            self._log(f"  {self.TARGET_MODULE} not found in process")
            return None
        base, size = module_info
        self._log(f"  {self.TARGET_MODULE}: base=0x{base:X}, size={size / 1024 / 1024:.1f} MB")
        image = self._read_module_image(handle, base, size)
        addr = self._resolve_target_framerate(image, base)
        if addr:
            self._cached_pid, self._cached_addr = pid, addr
            self._log(f"  targetFrameRate located at {self.TARGET_MODULE}+0x{addr - base:X}")
        return addr

    def _read_int(self, handle: int, addr: int) -> Optional[int]:
        data = self.read_memory(handle, addr, 4)
        if data and len(data) == 4:
            return struct.unpack("<i", data)[0]
        return None

    def read_current_cap(self) -> Optional[int]:
        """Read the game's current targetFrameRate (None if unavailable)."""
        pid = self.find_process()
        if pid is None:
            return None
        handle = kernel32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
        if not handle:
            return None
        try:
            addr = self._get_address(handle, pid)
            return self._read_int(handle, addr) if addr else None
        finally:
            kernel32.CloseHandle(handle)

    # ── Patching ────────────────────────────────────────────────────────

    def unlock_fps(self, target_fps: int = -1) -> PatchResult:
        """Set Unity's Application.targetFrameRate in the running game.

        Args:
            target_fps: The target FPS to set. -1 for unlimited.

        Returns:
            PatchResult with success status and details.
        """
        fps_label = "Unlimited" if target_fps < 0 else str(target_fps)

        self._log("Step 1: Finding SCPSL.exe process...")
        pid = self.find_process()
        if pid is None:
            return PatchResult(False, "SCPSL.exe process not found. Is the game running?")
        self._log(f"  Found SCPSL.exe (PID: {pid})")

        self._log("Step 2: Opening process...")
        handle = kernel32.OpenProcess(PROCESS_ACCESS, False, pid)
        if not handle:
            error = ctypes.get_last_error()
            return PatchResult(False, f"Failed to open process (Error: {error}). "
                                      "Try running as Administrator.")

        try:
            self._log("Step 3: Locating targetFrameRate...")
            addr = self._get_address(handle, pid)
            if not addr:
                return PatchResult(False, "Could not locate targetFrameRate in UnityPlayer.dll "
                                          "(game engine layout changed).")

            current = self._read_int(handle, addr)
            self._log(f"  Current FPS cap: {current}")
            if current is None or not (-1 <= current <= 10000):
                self._cached_pid = self._cached_addr = None
                return PatchResult(False, f"Unexpected value at target address ({current}); "
                                          "aborting for safety.", addresses_found=1)

            self._log(f"Step 4: Writing {fps_label}...")
            if not self.write_memory(handle, addr, struct.pack("<i", target_fps)):
                return PatchResult(False, "Failed to write memory. Try running as Administrator.",
                                   addresses_found=1)

            verify = self._read_int(handle, addr)
            if verify != target_fps:
                return PatchResult(False, f"Write did not stick (read back {verify}).",
                                   addresses_found=1)

            self._log(f"  ✅ FPS cap changed: {current} → {fps_label}")
            return PatchResult(True, f"FPS cap changed from {current} to {fps_label}!",
                               addresses_found=1, addresses_patched=1)
        finally:
            kernel32.CloseHandle(handle)

    # ── Keep-alive ──────────────────────────────────────────────────────

    def is_keepalive_running(self) -> bool:
        return bool(self._keepalive_thread and self._keepalive_thread.is_alive())

    def start_keepalive(self, target_fps: int = -1):
        """Re-apply the FPS value whenever the game resets it (e.g. on settings/scene change)."""
        self.stop_keepalive()
        stop = threading.Event()
        self._keepalive_stop = stop

        def loop():
            pid = self.find_process()
            if pid is None:
                return
            handle = kernel32.OpenProcess(PROCESS_ACCESS, False, pid)
            if not handle:
                self._log("Keep-alive: failed to open process")
                return
            try:
                addr = self._get_address(handle, pid)
                if not addr:
                    return
                self._log("🔁 Keep-alive started — FPS cap will be re-applied if the game resets it")
                packed = struct.pack("<i", target_fps)
                exit_code = ctypes.c_uint(0)
                while not stop.wait(self.KEEPALIVE_INTERVAL):
                    if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)) \
                            or exit_code.value != STILL_ACTIVE:
                        self._log("Keep-alive: game closed, stopping")
                        break
                    value = self._read_int(handle, addr)
                    if value is not None and value != target_fps:
                        if self.write_memory(handle, addr, packed):
                            self._log(f"🔁 Game reset FPS cap to {value} — re-applied")
            finally:
                kernel32.CloseHandle(handle)

        self._keepalive_thread = threading.Thread(target=loop, daemon=True)
        self._keepalive_thread.start()

    def stop_keepalive(self):
        if self._keepalive_stop:
            self._keepalive_stop.set()
        if self._keepalive_thread and self._keepalive_thread is not threading.current_thread():
            self._keepalive_thread.join(timeout=3)
        self._keepalive_thread = None
        self._keepalive_stop = None

    # ── Legacy helper (kept for API compatibility) ──────────────────────

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
