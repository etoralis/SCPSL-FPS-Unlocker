"""
SCPSL FPS Unlocker - Main Application
A tool to unlock FPS in SCP: Secret Laboratory

Author: SCPSL FPS Unlocker Contributors
License: MIT
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import datetime
import sys
import os
import ctypes

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.diagnostics import SystemDiagnostics, SystemInfo
from modules.config_fixer import ConfigFixer, FixResult
from modules.memory_patcher import MemoryPatcher, PatchResult


# ─── Color Palette ──────────────────────────────────────────────────────────
class Colors:
    BG_DARK = "#0d1117"
    BG_CARD = "#161b22"
    BG_INPUT = "#21262d"
    BG_HOVER = "#30363d"
    BORDER = "#30363d"
    TEXT = "#e6edf3"
    TEXT_DIM = "#8b949e"
    TEXT_MUTED = "#6e7681"
    ACCENT_BLUE = "#58a6ff"
    ACCENT_GREEN = "#3fb950"
    ACCENT_RED = "#f85149"
    ACCENT_ORANGE = "#d29922"
    ACCENT_PURPLE = "#bc8cff"
    GRADIENT_START = "#1a1b27"
    GRADIENT_END = "#0d1117"


# ─── Dark Theme Setup ───────────────────────────────────────────────────────
def apply_dark_theme(root: tk.Tk) -> ttk.Style:
    """Apply a modern dark theme to the application."""
    style = ttk.Style()
    style.theme_use("clam")

    # General
    style.configure(".", background=Colors.BG_DARK, foreground=Colors.TEXT,
                     fieldbackground=Colors.BG_INPUT, borderwidth=0,
                     font=("Segoe UI", 10))

    # Notebook (tabs)
    style.configure("TNotebook", background=Colors.BG_DARK, borderwidth=0,
                     padding=0)
    style.configure("TNotebook.Tab", background=Colors.BG_CARD,
                     foreground=Colors.TEXT_DIM, padding=[20, 10],
                     font=("Segoe UI Semibold", 10))
    style.map("TNotebook.Tab",
              background=[("selected", Colors.BG_DARK), ("active", Colors.BG_HOVER)],
              foreground=[("selected", Colors.ACCENT_BLUE), ("active", Colors.TEXT)])

    # Frames
    style.configure("TFrame", background=Colors.BG_DARK)
    style.configure("Card.TFrame", background=Colors.BG_CARD)

    # Labels
    style.configure("TLabel", background=Colors.BG_DARK, foreground=Colors.TEXT,
                     font=("Segoe UI", 10))
    style.configure("Title.TLabel", font=("Segoe UI Semibold", 18),
                     foreground=Colors.ACCENT_BLUE, background=Colors.BG_DARK)
    style.configure("Subtitle.TLabel", font=("Segoe UI", 11),
                     foreground=Colors.TEXT_DIM, background=Colors.BG_DARK)
    style.configure("CardTitle.TLabel", font=("Segoe UI Semibold", 12),
                     foreground=Colors.TEXT, background=Colors.BG_CARD)
    style.configure("Status.OK.TLabel", foreground=Colors.ACCENT_GREEN,
                     background=Colors.BG_CARD, font=("Segoe UI", 10))
    style.configure("Status.Warn.TLabel", foreground=Colors.ACCENT_ORANGE,
                     background=Colors.BG_CARD, font=("Segoe UI", 10))
    style.configure("Status.Error.TLabel", foreground=Colors.ACCENT_RED,
                     background=Colors.BG_CARD, font=("Segoe UI", 10))
    style.configure("Status.Info.TLabel", foreground=Colors.ACCENT_BLUE,
                     background=Colors.BG_CARD, font=("Segoe UI", 10))

    # Buttons
    style.configure("Accent.TButton", background=Colors.ACCENT_BLUE,
                     foreground="#ffffff", font=("Segoe UI Semibold", 10),
                     padding=[20, 10])
    style.map("Accent.TButton",
              background=[("active", "#79c0ff"), ("disabled", Colors.BG_HOVER)])

    style.configure("Success.TButton", background=Colors.ACCENT_GREEN,
                     foreground="#ffffff", font=("Segoe UI Semibold", 10),
                     padding=[20, 10])
    style.map("Success.TButton",
              background=[("active", "#56d364"), ("disabled", Colors.BG_HOVER)])

    style.configure("Danger.TButton", background=Colors.ACCENT_RED,
                     foreground="#ffffff", font=("Segoe UI Semibold", 10),
                     padding=[20, 10])
    style.map("Danger.TButton",
              background=[("active", "#ff7b72"), ("disabled", Colors.BG_HOVER)])

    style.configure("Secondary.TButton", background=Colors.BG_HOVER,
                     foreground=Colors.TEXT, font=("Segoe UI", 10),
                     padding=[16, 8])
    style.map("Secondary.TButton",
              background=[("active", Colors.BORDER)])

    # Separator
    style.configure("TSeparator", background=Colors.BORDER)

    # Progressbar
    style.configure("TProgressbar", background=Colors.ACCENT_BLUE,
                     troughcolor=Colors.BG_INPUT, borderwidth=0, thickness=6)

    # Combobox
    style.configure("TCombobox", fieldbackground=Colors.BG_INPUT,
                     background=Colors.BG_HOVER, foreground=Colors.TEXT,
                     selectbackground=Colors.ACCENT_BLUE,
                     selectforeground="#ffffff")

    # Spinbox
    style.configure("TSpinbox", fieldbackground=Colors.BG_INPUT,
                     background=Colors.BG_HOVER, foreground=Colors.TEXT)

    return style


# ─── Helper: Card Frame ─────────────────────────────────────────────────────
def create_card(parent, title: str = "", padding: int = 16) -> ttk.Frame:
    """Create a styled card container."""
    outer = tk.Frame(parent, bg=Colors.BG_CARD, highlightbackground=Colors.BORDER,
                     highlightthickness=1, bd=0)
    inner = tk.Frame(outer, bg=Colors.BG_CARD, padx=padding, pady=padding)
    inner.pack(fill="both", expand=True)
    if title:
        lbl = tk.Label(inner, text=title, font=("Segoe UI Semibold", 12),
                       bg=Colors.BG_CARD, fg=Colors.TEXT, anchor="w")
        lbl.pack(fill="x", pady=(0, 10))
        sep = tk.Frame(inner, bg=Colors.BORDER, height=1)
        sep.pack(fill="x", pady=(0, 10))
    return outer, inner


def create_status_row(parent, label_text: str, value_text: str,
                      status: str = "info") -> tuple[tk.Label, tk.Label]:
    """Create a label-value row inside a card."""
    row = tk.Frame(parent, bg=Colors.BG_CARD)
    row.pack(fill="x", pady=3)

    lbl = tk.Label(row, text=label_text, font=("Segoe UI", 10),
                   bg=Colors.BG_CARD, fg=Colors.TEXT_DIM, anchor="w", width=28)
    lbl.pack(side="left")

    color_map = {
        "ok": Colors.ACCENT_GREEN,
        "warn": Colors.ACCENT_ORANGE,
        "error": Colors.ACCENT_RED,
        "info": Colors.ACCENT_BLUE,
        "text": Colors.TEXT,
    }
    fg = color_map.get(status, Colors.TEXT)
    val = tk.Label(row, text=value_text, font=("Segoe UI Semibold", 10),
                   bg=Colors.BG_CARD, fg=fg, anchor="w")
    val.pack(side="left", fill="x", expand=True)
    return lbl, val


# ─── Main Application ───────────────────────────────────────────────────────
class FPSUnlockerApp:
    VERSION = "1.0.0"

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"SCPSL FPS Unlocker v{self.VERSION}")
        self.root.geometry("820x680")
        self.root.minsize(780, 600)
        self.root.configure(bg=Colors.BG_DARK)

        # Try to set icon
        try:
            self.root.iconbitmap(os.path.join(os.path.dirname(__file__), "assets", "icon.ico"))
        except Exception:
            pass

        # Apply theme
        self.style = apply_dark_theme(self.root)

        # State
        self.diagnostics = SystemDiagnostics()
        self.config_fixer = None  # Initialized after game detection
        self.memory_patcher = MemoryPatcher(log_callback=self.log)
        self.system_info: SystemInfo | None = None
        self.log_messages: list[str] = []

        # Build UI
        self._build_header()
        self._build_notebook()
        self._build_status_bar()

        # Run initial diagnostics
        self.root.after(300, self._run_diagnostics)

    def _build_header(self):
        """Build the application header."""
        header = tk.Frame(self.root, bg=Colors.BG_DARK, padx=24, pady=16)
        header.pack(fill="x")

        title_frame = tk.Frame(header, bg=Colors.BG_DARK)
        title_frame.pack(fill="x")

        tk.Label(title_frame, text="⚡ SCPSL FPS Unlocker",
                 font=("Segoe UI Semibold", 20), bg=Colors.BG_DARK,
                 fg=Colors.ACCENT_BLUE).pack(side="left")

        tk.Label(title_frame, text=f"v{self.VERSION}",
                 font=("Segoe UI", 10), bg=Colors.BG_DARK,
                 fg=Colors.TEXT_MUTED).pack(side="left", padx=(8, 0), pady=(8, 0))

        tk.Label(header, text="Break free from the 60 FPS cap in SCP: Secret Laboratory",
                 font=("Segoe UI", 10), bg=Colors.BG_DARK,
                 fg=Colors.TEXT_DIM).pack(anchor="w", pady=(4, 0))

    def _build_notebook(self):
        """Build the tabbed interface."""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        # Tab 1: Diagnostics
        self.tab_diag = tk.Frame(self.notebook, bg=Colors.BG_DARK)
        self.notebook.add(self.tab_diag, text="  🔍 Diagnostics  ")
        self._build_diagnostics_tab()

        # Tab 2: Quick Fix
        self.tab_fix = tk.Frame(self.notebook, bg=Colors.BG_DARK)
        self.notebook.add(self.tab_fix, text="  🔧 Quick Fix  ")
        self._build_quickfix_tab()

        # Tab 3: Advanced
        self.tab_adv = tk.Frame(self.notebook, bg=Colors.BG_DARK)
        self.notebook.add(self.tab_adv, text="  ⚠️ Advanced  ")
        self._build_advanced_tab()

        # Tab 4: Log
        self.tab_log = tk.Frame(self.notebook, bg=Colors.BG_DARK)
        self.notebook.add(self.tab_log, text="  📋 Log  ")
        self._build_log_tab()

    def _build_diagnostics_tab(self):
        """Build the diagnostics tab content."""
        container = tk.Frame(self.tab_diag, bg=Colors.BG_DARK, padx=8, pady=8)
        container.pack(fill="both", expand=True)

        # System Info Card
        card_outer, card_inner = create_card(container, title="💻 System Information")
        card_outer.pack(fill="x", pady=(0, 8))
        self.diag_system_frame = card_inner

        # Game Info Card
        card_outer2, card_inner2 = create_card(container, title="🎮 Game Information")
        card_outer2.pack(fill="x", pady=(0, 8))
        self.diag_game_frame = card_inner2

        # Issues Card
        card_outer3, card_inner3 = create_card(container, title="⚡ Detected Issues")
        card_outer3.pack(fill="x", pady=(0, 8))
        self.diag_issues_frame = card_inner3

        # Refresh button
        btn_frame = tk.Frame(container, bg=Colors.BG_DARK)
        btn_frame.pack(fill="x", pady=(4, 0))
        ttk.Button(btn_frame, text="🔄 Refresh Diagnostics",
                   style="Secondary.TButton",
                   command=self._run_diagnostics).pack(side="right")

    def _build_quickfix_tab(self):
        """Build the quick fix tab content."""
        container = tk.Frame(self.tab_fix, bg=Colors.BG_DARK, padx=8, pady=8)
        container.pack(fill="both", expand=True)

        # Description
        desc_frame = tk.Frame(container, bg=Colors.BG_DARK)
        desc_frame.pack(fill="x", pady=(0, 12))
        tk.Label(desc_frame,
                 text="These fixes are safe, config-based changes that can be fully reversed.",
                 font=("Segoe UI", 10), bg=Colors.BG_DARK,
                 fg=Colors.TEXT_DIM, wraplength=700, justify="left").pack(anchor="w")

        # Fix options
        self.fix_vars = {}

        fixes = [
            ("gamedvr", "🛡️ Disable Windows GameDVR",
             "Disables Windows Game DVR/Game Bar which can cap FPS to 60"),
            ("boot_config", "📄 Optimize Boot Config",
             "Modifies SCPSL_Data/boot.config for better performance"),
            ("fullscreen", "🖥️ Switch to Exclusive Fullscreen",
             "Changes from Borderless to Exclusive Fullscreen (bypasses DWM)"),
        ]

        for key, title, desc in fixes:
            card_outer, card_inner = create_card(container)
            card_outer.pack(fill="x", pady=(0, 6))

            row = tk.Frame(card_inner, bg=Colors.BG_CARD)
            row.pack(fill="x")

            var = tk.BooleanVar(value=True)
            self.fix_vars[key] = var

            cb = tk.Checkbutton(row, variable=var, bg=Colors.BG_CARD,
                                fg=Colors.TEXT, selectcolor=Colors.BG_INPUT,
                                activebackground=Colors.BG_CARD,
                                activeforeground=Colors.TEXT,
                                font=("Segoe UI Semibold", 11),
                                text=title, anchor="w")
            cb.pack(side="left", fill="x")

            tk.Label(card_inner, text=desc, font=("Segoe UI", 9),
                     bg=Colors.BG_CARD, fg=Colors.TEXT_DIM,
                     anchor="w").pack(fill="x", pady=(4, 0))

        # Steam launch hint card
        card_outer_steam, card_inner_steam = create_card(container, title="🚀 Steam Launch Options (Manual)")
        card_outer_steam.pack(fill="x", pady=(0, 6))
        tk.Label(card_inner_steam,
                 text="Steam → SCP:SL → Properties → Launch Options →  Add:",
                 font=("Segoe UI", 10), bg=Colors.BG_CARD,
                 fg=Colors.TEXT_DIM, anchor="w").pack(fill="x")

        cmd_frame = tk.Frame(card_inner_steam, bg=Colors.BG_INPUT, padx=12, pady=8)
        cmd_frame.pack(fill="x", pady=(6, 0))
        self.steam_cmd_label = tk.Label(cmd_frame,
                 text="-screen-fullscreen 1 -window-mode exclusive",
                 font=("Consolas", 11), bg=Colors.BG_INPUT,
                 fg=Colors.ACCENT_GREEN, anchor="w")
        self.steam_cmd_label.pack(fill="x")

        # Buttons
        btn_frame = tk.Frame(container, bg=Colors.BG_DARK)
        btn_frame.pack(fill="x", pady=(12, 0))

        ttk.Button(btn_frame, text="✅ Apply Selected Fixes",
                   style="Success.TButton",
                   command=self._apply_fixes).pack(side="left", padx=(0, 8))

        ttk.Button(btn_frame, text="↩️ Restore All",
                   style="Secondary.TButton",
                   command=self._restore_fixes).pack(side="left")

    def _build_advanced_tab(self):
        """Build the advanced (memory patcher) tab."""
        container = tk.Frame(self.tab_adv, bg=Colors.BG_DARK, padx=8, pady=8)
        container.pack(fill="both", expand=True)

        # Warning banner
        warn_outer = tk.Frame(container, bg=Colors.ACCENT_RED,
                              highlightbackground=Colors.ACCENT_RED,
                              highlightthickness=1)
        warn_outer.pack(fill="x", pady=(0, 12))
        warn_inner = tk.Frame(warn_outer, bg="#2d1b1e", padx=16, pady=12)
        warn_inner.pack(fill="both")
        tk.Label(warn_inner, text="⚠️  WARNING — Anti-Cheat Risk",
                 font=("Segoe UI Semibold", 12), bg="#2d1b1e",
                 fg=Colors.ACCENT_RED, anchor="w").pack(fill="x")
        tk.Label(warn_inner,
                 text="This feature modifies game memory at runtime. SL-AC anti-cheat may "
                      "detect this and result in a BAN. Use at your own risk. "
                      "Test on private/local servers first.",
                 font=("Segoe UI", 10), bg="#2d1b1e", fg="#f8a4a0",
                 wraplength=680, justify="left", anchor="w").pack(fill="x", pady=(6, 0))

        # Memory patcher options
        card_outer, card_inner = create_card(container, title="🧠 Runtime FPS Patch")
        card_outer.pack(fill="x", pady=(0, 8))

        # Target FPS selection
        fps_frame = tk.Frame(card_inner, bg=Colors.BG_CARD)
        fps_frame.pack(fill="x", pady=(0, 8))

        tk.Label(fps_frame, text="Target FPS:", font=("Segoe UI", 10),
                 bg=Colors.BG_CARD, fg=Colors.TEXT_DIM).pack(side="left")

        self.target_fps_var = tk.StringVar(value="Unlimited (-1)")
        fps_options = ["Unlimited (-1)", "120", "144", "165", "240", "360"]
        fps_combo = ttk.Combobox(fps_frame, textvariable=self.target_fps_var,
                                  values=fps_options, state="readonly", width=18)
        fps_combo.pack(side="left", padx=(8, 0))

        # Game status
        status_frame = tk.Frame(card_inner, bg=Colors.BG_CARD)
        status_frame.pack(fill="x", pady=(0, 8))

        tk.Label(status_frame, text="Game Status:", font=("Segoe UI", 10),
                 bg=Colors.BG_CARD, fg=Colors.TEXT_DIM).pack(side="left")

        self.game_status_label = tk.Label(status_frame, text="⏳ Checking...",
                                           font=("Segoe UI Semibold", 10),
                                           bg=Colors.BG_CARD, fg=Colors.TEXT_MUTED)
        self.game_status_label.pack(side="left", padx=(8, 0))

        # Patch button
        btn_frame = tk.Frame(card_inner, bg=Colors.BG_CARD)
        btn_frame.pack(fill="x", pady=(8, 0))

        self.patch_btn = ttk.Button(btn_frame, text="🚀 Patch FPS (Game Must Be Running)",
                                     style="Danger.TButton",
                                     command=self._apply_memory_patch)
        self.patch_btn.pack(side="left")

        ttk.Button(btn_frame, text="🔄 Check Game",
                   style="Secondary.TButton",
                   command=self._check_game_status).pack(side="left", padx=(8, 0))

        # How it works
        card_outer2, card_inner2 = create_card(container, title="📖 How Runtime Patching Works")
        card_outer2.pack(fill="x", pady=(0, 8))

        steps = [
            "1. Finds the running SCPSL.exe process",
            "2. Locates UnityPlayer.dll in process memory",
            "3. Scans for the frame rate cap value (60)",
            "4. Patches it to your target FPS or unlimited",
            "5. The patch lasts until the game is restarted",
        ]
        for step in steps:
            tk.Label(card_inner2, text=step, font=("Segoe UI", 10),
                     bg=Colors.BG_CARD, fg=Colors.TEXT_DIM,
                     anchor="w").pack(fill="x", pady=1)

    def _build_log_tab(self):
        """Build the log viewer tab."""
        container = tk.Frame(self.tab_log, bg=Colors.BG_DARK, padx=8, pady=8)
        container.pack(fill="both", expand=True)

        # Log text area
        self.log_text = scrolledtext.ScrolledText(
            container, bg=Colors.BG_CARD, fg=Colors.TEXT,
            font=("Consolas", 10), insertbackground=Colors.TEXT,
            selectbackground=Colors.ACCENT_BLUE,
            selectforeground="#ffffff", relief="flat",
            highlightbackground=Colors.BORDER, highlightthickness=1,
            padx=12, pady=12, state="disabled", wrap="word"
        )
        self.log_text.pack(fill="both", expand=True, pady=(0, 8))

        # Configure log text tags for colors
        self.log_text.tag_configure("info", foreground=Colors.ACCENT_BLUE)
        self.log_text.tag_configure("success", foreground=Colors.ACCENT_GREEN)
        self.log_text.tag_configure("warning", foreground=Colors.ACCENT_ORANGE)
        self.log_text.tag_configure("error", foreground=Colors.ACCENT_RED)
        self.log_text.tag_configure("timestamp", foreground=Colors.TEXT_MUTED)

        # Buttons
        btn_frame = tk.Frame(container, bg=Colors.BG_DARK)
        btn_frame.pack(fill="x")

        ttk.Button(btn_frame, text="🗑️ Clear Log",
                   style="Secondary.TButton",
                   command=self._clear_log).pack(side="right")

        ttk.Button(btn_frame, text="💾 Save Log",
                   style="Secondary.TButton",
                   command=self._save_log).pack(side="right", padx=(0, 8))

    def _build_status_bar(self):
        """Build the bottom status bar."""
        status_bar = tk.Frame(self.root, bg=Colors.BG_CARD, height=32)
        status_bar.pack(fill="x", side="bottom")
        status_bar.pack_propagate(False)

        inner = tk.Frame(status_bar, bg=Colors.BG_CARD, padx=16)
        inner.pack(fill="both", expand=True)

        self.status_label = tk.Label(inner, text="⏳ Initializing...",
                                      font=("Segoe UI", 9), bg=Colors.BG_CARD,
                                      fg=Colors.TEXT_DIM, anchor="w")
        self.status_label.pack(side="left", fill="x", expand=True)

        tk.Label(inner, text="Made with ❤️ for the SCP:SL community",
                 font=("Segoe UI", 9), bg=Colors.BG_CARD,
                 fg=Colors.TEXT_MUTED).pack(side="right")

    # ── Diagnostics ──────────────────────────────────────────────────────

    def _run_diagnostics(self):
        """Run system diagnostics in a background thread."""
        self.set_status("🔍 Running diagnostics...")
        self.log("Starting system diagnostics...", "info")

        def run():
            try:
                info = self.diagnostics.get_full_diagnostics()
                self.system_info = info
                self.root.after(0, lambda: self._update_diagnostics_ui(info))
            except Exception as e:
                self.root.after(0, lambda: self.log(f"Diagnostics error: {e}", "error"))
                self.root.after(0, lambda: self.set_status("❌ Diagnostics failed"))

        threading.Thread(target=run, daemon=True).start()

    def _update_diagnostics_ui(self, info: SystemInfo):
        """Update the diagnostics tab with gathered info."""
        # Clear existing widgets in system frame (except title and separator)
        for widget in self.diag_system_frame.winfo_children():
            if isinstance(widget, tk.Frame) and widget.winfo_children():
                # Check if it's a status row
                first_child = widget.winfo_children()[0] if widget.winfo_children() else None
                if first_child and isinstance(first_child, tk.Label):
                    widget.destroy()

        # System info
        create_status_row(self.diag_system_frame, "GPU",
                          info.gpu_name,
                          "ok" if "RTX" in info.gpu_name or "RX" in info.gpu_name else "text")
        create_status_row(self.diag_system_frame, "Driver Version",
                          info.gpu_driver, "text")
        create_status_row(self.diag_system_frame, "Monitor",
                          f"{info.monitor_resolution} @ {info.monitor_refresh_rate}Hz",
                          "ok" if info.monitor_refresh_rate > 60 else "warn")
        create_status_row(self.diag_system_frame, "Power Plan",
                          info.power_plan,
                          "ok" if "yüksek" in info.power_plan.lower()
                          or "high" in info.power_plan.lower()
                          or "ultimate" in info.power_plan.lower() else "warn")
        create_status_row(self.diag_system_frame, "GameDVR",
                          "Enabled ❌" if info.game_dvr_enabled else "Disabled ✅",
                          "error" if info.game_dvr_enabled else "ok")

        # Game info
        for widget in self.diag_game_frame.winfo_children():
            if isinstance(widget, tk.Frame) and widget.winfo_children():
                first_child = widget.winfo_children()[0] if widget.winfo_children() else None
                if first_child and isinstance(first_child, tk.Label):
                    widget.destroy()

        if info.game_path:
            create_status_row(self.diag_game_frame, "Installation",
                              info.game_path, "ok")
            create_status_row(self.diag_game_frame, "Engine",
                              "Unity IL2CPP" if info.is_il2cpp else "Unity Mono",
                              "info")
            create_status_row(self.diag_game_frame, "Anti-Cheat",
                              "SL-AC Detected ⚠️" if info.has_anticheat else "Not Detected",
                              "warn" if info.has_anticheat else "ok")
            create_status_row(self.diag_game_frame, "Fullscreen Mode",
                              info.fullscreen_mode_name,
                              "warn" if info.fullscreen_mode == 1 else "ok")

            # Initialize config fixer
            self.config_fixer = ConfigFixer(info.game_path)
        else:
            create_status_row(self.diag_game_frame, "Installation",
                              "NOT FOUND ❌", "error")

        # Issues
        for widget in self.diag_issues_frame.winfo_children():
            if isinstance(widget, tk.Frame) and widget.winfo_children():
                first_child = widget.winfo_children()[0] if widget.winfo_children() else None
                if first_child and isinstance(first_child, tk.Label):
                    widget.destroy()

        issues_found = False

        if info.game_dvr_enabled:
            create_status_row(self.diag_issues_frame, "❌ GameDVR",
                              "Enabled — can cause 60 FPS cap!", "error")
            issues_found = True

        if info.fullscreen_mode == 1:
            create_status_row(self.diag_issues_frame, "⚠️ Fullscreen",
                              "Borderless mode — DWM may limit FPS", "warn")
            issues_found = True

        if info.monitor_refresh_rate <= 60:
            create_status_row(self.diag_issues_frame, "⚠️ Monitor",
                              f"Only {info.monitor_refresh_rate}Hz detected", "warn")
            issues_found = True

        if not info.game_path:
            create_status_row(self.diag_issues_frame, "❌ Game",
                              "SCP:SL installation not found", "error")
            issues_found = True

        if not issues_found:
            create_status_row(self.diag_issues_frame, "✅ Status",
                              "No obvious config issues found — try Advanced tab", "ok")

        self.log("Diagnostics completed successfully", "success")
        self.set_status("✅ Diagnostics complete")
        self._check_game_status()

    # ── Quick Fix ────────────────────────────────────────────────────────

    def _apply_fixes(self):
        """Apply selected config fixes."""
        if not self.config_fixer:
            messagebox.showerror("Error", "Game installation not found. Run diagnostics first.")
            return

        self.set_status("🔧 Applying fixes...")
        self.log("Applying selected fixes...", "info")

        def run():
            results: list[FixResult] = []

            if self.fix_vars.get("gamedvr", tk.BooleanVar()).get():
                self.root.after(0, lambda: self.log("  Fixing GameDVR...", "info"))
                r = self.config_fixer.fix_game_dvr()
                results.append(r)
                tag = "success" if r.success else "error"
                self.root.after(0, lambda r=r, t=tag: self.log(f"    → {r.message}", t))

            if self.fix_vars.get("boot_config", tk.BooleanVar()).get():
                self.root.after(0, lambda: self.log("  Fixing boot.config...", "info"))
                r = self.config_fixer.fix_boot_config()
                results.append(r)
                tag = "success" if r.success else "error"
                self.root.after(0, lambda r=r, t=tag: self.log(f"    → {r.message}", t))

            if self.fix_vars.get("fullscreen", tk.BooleanVar()).get():
                self.root.after(0, lambda: self.log("  Fixing fullscreen mode...", "info"))
                r = self.config_fixer.fix_fullscreen_mode(0)
                results.append(r)
                tag = "success" if r.success else "error"
                self.root.after(0, lambda r=r, t=tag: self.log(f"    → {r.message}", t))

            success_count = sum(1 for r in results if r.success)
            total = len(results)

            self.root.after(0, lambda: self.log(
                f"Fixes complete: {success_count}/{total} successful", "success"))
            self.root.after(0, lambda: self.set_status(
                f"✅ Applied {success_count}/{total} fixes — restart the game to apply"))
            self.root.after(0, lambda: messagebox.showinfo(
                "Fixes Applied",
                f"Successfully applied {success_count}/{total} fixes.\n\n"
                "Please restart SCP: Secret Laboratory for changes to take effect.\n\n"
                "Also add these Steam launch options:\n"
                "-screen-fullscreen 1 -window-mode exclusive"))

        threading.Thread(target=run, daemon=True).start()

    def _restore_fixes(self):
        """Restore all backed up values."""
        if not self.config_fixer:
            messagebox.showerror("Error", "Game installation not found.")
            return

        if not messagebox.askyesno("Confirm Restore",
                                    "Restore all settings to their original values?"):
            return

        self.log("Restoring original settings...", "info")

        def run():
            results = self.config_fixer.restore_all()
            for r in results:
                tag = "success" if r.success else "error"
                self.root.after(0, lambda r=r, t=tag: self.log(f"  → {r.message}", t))
            self.root.after(0, lambda: self.set_status("↩️ Settings restored"))
            self.root.after(0, lambda: self.log("Restore complete", "success"))

        threading.Thread(target=run, daemon=True).start()

    # ── Advanced ─────────────────────────────────────────────────────────

    def _check_game_status(self):
        """Check if the game is currently running."""
        def run():
            is_running = self.memory_patcher.is_game_running()
            if is_running:
                self.root.after(0, lambda: self.game_status_label.config(
                    text="🟢 Game is running", fg=Colors.ACCENT_GREEN))
            else:
                self.root.after(0, lambda: self.game_status_label.config(
                    text="🔴 Game is not running", fg=Colors.ACCENT_RED))

        threading.Thread(target=run, daemon=True).start()

    def _apply_memory_patch(self):
        """Apply the runtime memory patch."""
        if not messagebox.askyesno(
                "⚠️ Warning",
                "This will modify game memory at runtime.\n\n"
                "RISKS:\n"
                "• SL-AC anti-cheat may detect this\n"
                "• You could receive a game ban\n"
                "• Use on private/local servers first\n\n"
                "Do you want to continue?",
                icon="warning"):
            return

        # Parse target FPS
        fps_str = self.target_fps_var.get()
        if "Unlimited" in fps_str or "-1" in fps_str:
            target_fps = -1
        else:
            try:
                target_fps = int(fps_str)
            except ValueError:
                target_fps = -1

        self.set_status(f"🧠 Patching FPS to {target_fps if target_fps > 0 else 'Unlimited'}...")
        self.log(f"Starting memory patch (target: {target_fps})...", "warning")
        self.patch_btn.state(["disabled"])

        def run():
            try:
                result = self.memory_patcher.unlock_fps(target_fps)
                tag = "success" if result.success else "error"
                self.root.after(0, lambda: self.log(
                    f"Patch result: {result.message} "
                    f"(found: {result.addresses_found}, patched: {result.addresses_patched})",
                    tag))
                if result.success:
                    self.root.after(0, lambda: self.set_status("✅ FPS patch applied!"))
                else:
                    self.root.after(0, lambda: self.set_status(f"❌ {result.message}"))
            except Exception as e:
                self.root.after(0, lambda: self.log(f"Patch error: {e}", "error"))
                self.root.after(0, lambda: self.set_status("❌ Patch failed"))
            finally:
                self.root.after(0, lambda: self.patch_btn.state(["!disabled"]))

        threading.Thread(target=run, daemon=True).start()

    # ── Logging ──────────────────────────────────────────────────────────

    def log(self, message: str, level: str = "info"):
        """Add a message to the log."""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        full_msg = f"[{timestamp}] {message}"
        self.log_messages.append(full_msg)

        def update():
            self.log_text.configure(state="normal")
            self.log_text.insert("end", f"[{timestamp}] ", "timestamp")
            self.log_text.insert("end", f"{message}\n", level)
            self.log_text.see("end")
            self.log_text.configure(state="disabled")

        if threading.current_thread() is threading.main_thread():
            update()
        else:
            self.root.after(0, update)

    def _clear_log(self):
        """Clear the log text."""
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
        self.log_messages.clear()

    def _save_log(self):
        """Save log to a file."""
        from tkinter import filedialog
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"scpsl_fps_unlocker_{datetime.datetime.now():%Y%m%d_%H%M%S}.txt"
        )
        if filepath:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("\n".join(self.log_messages))
            self.log(f"Log saved to {filepath}", "success")

    def set_status(self, text: str):
        """Update the status bar text."""
        self.status_label.config(text=text)

    # ── Run ──────────────────────────────────────────────────────────────

    def run(self):
        """Start the application."""
        self.root.mainloop()


# ─── Entry Point ─────────────────────────────────────────────────────────────
def main():
    # Check if running on Windows
    if sys.platform != "win32":
        print("This tool only works on Windows.")
        sys.exit(1)

    # Check admin privileges (optional, show warning if not admin)
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        is_admin = False

    app = FPSUnlockerApp()

    if not is_admin:
        app.log("Running without admin privileges — some features may be limited", "warning")
        app.log("Tip: Run with run_admin.bat for full functionality", "info")

    app.run()


if __name__ == "__main__":
    main()
