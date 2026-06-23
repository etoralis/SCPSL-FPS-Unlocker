<h1 align="center">
  🎮 SCPSL FPS Unlocker
</h1>

<p align="center">
  <strong>Unlock your FPS in SCP: Secret Laboratory. Break free from the 60 FPS cap.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white" alt="Windows">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="MIT License">
</p>

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔍 **Auto-Detection** | Automatically finds your SCP:SL installation via Steam |
| 🩺 **System Diagnostics** | Scans your system for FPS-limiting issues |
| ⚙️ **Boot.config Optimization** | Patches Unity engine config for uncapped framerate |
| 🎬 **GameDVR Disable** | Disables Windows GameDVR / Game Bar overlays that tank FPS |
| 🖥️ **Fullscreen Mode Switching** | Switches between Exclusive Fullscreen, Borderless, and Windowed |
| 🗝️ **Registry Optimization** | Applies Windows registry tweaks for gaming performance |
| 🧠 **Runtime Memory Patching** | Advanced: patches the running game process in memory |
| 🚀 **One-Click Fix All** | Applies all safe optimizations in a single click |
| 💾 **Backup & Restore** | Creates backups before any changes so you can always revert |

---

## 📸 Screenshots

> _Screenshots coming soon._

---

## 📦 Installation

```bash
git clone https://github.com/your-username/SCPSL-FPS-Unlocker.git
cd SCPSL-FPS-Unlocker
python main.py
```

> [!IMPORTANT]
> **Run as Administrator** for advanced features like registry optimization and memory patching.
>
> You can use `run_admin.bat` for an automatic UAC prompt.

### Requirements

- **Python 3.10+** — [Download](https://www.python.org/downloads/)
- **Windows 10/11**
- No external pip packages required (uses Python standard library only)

---

## 🚀 Usage

Launch the application and navigate through the tabs:

| Tab | What It Does |
|---|---|
| **🏠 Home** | System diagnostics — detects your game install, checks current FPS cap status, and scans for common issues |
| **⚙️ Config Fixes** | Edits `boot.config` and Unity player prefs to remove the framerate cap at the engine level |
| **🖥️ Display** | Switch between Exclusive Fullscreen, Borderless Windowed, and Windowed modes |
| **🗝️ Registry** | Applies Windows registry tweaks — disables GameDVR, Game Bar, and fullscreen optimizations |
| **🧠 Memory Patcher** | _(Advanced)_ Attaches to the running game process and patches the VSync / frame limiter in memory |
| **💾 Backup** | View, create, and restore backups of all modified files and registry keys |

---

## 🔧 How It Works

The FPS unlock process works in **3 phases**:

### Phase 1 — Static Config Patching
Modifies the game's `boot.config` file to set `maxfps=0` (uncapped) and disable VSync at the Unity engine level. These changes persist across game restarts.

### Phase 2 — System-Level Optimization
Applies Windows registry tweaks to disable performance-draining features like GameDVR, Game Bar overlay, and fullscreen optimizations that interfere with exclusive fullscreen mode.

### Phase 3 — Runtime Memory Patching _(Advanced)_
While the game is running, scans the process memory for the frame limiter routine and patches it in real-time. This bypasses any runtime FPS caps that survive the config changes.

---

## ⚠️ Warning & Disclaimer

> [!CAUTION]
> **Memory Patcher (Phase 3) modifies the running game process in memory.**
>
> While the config-based fixes (Phase 1 & 2) are safe and do not modify game code, the **runtime memory patcher** directly alters the game's process memory. This **may be flagged by anti-cheat systems**.
>
> - **Config fixes** → ✅ Safe — modifies external config files only
> - **Registry tweaks** → ✅ Safe — standard Windows optimizations
> - **Memory patcher** → ⚠️ **Use at your own risk** — may trigger anti-cheat
>
> The authors are **not responsible** for any bans, account suspensions, or other consequences resulting from the use of this tool. Use the memory patcher feature **at your own risk**.

---

## ❓ FAQ

### Why am I stuck at 60 FPS?
SCP: Secret Laboratory uses the Unity engine, which defaults to a 60 FPS cap via VSync. Windows features like GameDVR and fullscreen optimizations can also enforce a 60 FPS limit even when VSync is disabled in-game.

### Is this safe to use?
**Yes, for the config and registry fixes.** These are standard optimizations that modify external configuration files and Windows settings — they do not touch the game's executable or code. Many players use these exact same tweaks manually.

### Will I get banned?
- **Config fixes & registry tweaks:** No. These do not modify the game binary and are not detectable by anti-cheat.
- **Memory patcher:** **Possibly.** The runtime memory patcher modifies the game process in memory, which is the same technique used by cheats. While it only targets the frame limiter, anti-cheat systems may not distinguish this from malicious modifications. **Use at your own risk.**

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m "Add amazing feature"`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

Please make sure your code:
- Follows the existing code style
- Includes type hints
- Works on Windows 10/11
- Doesn't add external dependencies unless absolutely necessary

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  Made with ❤️ for the SCP:SL community
</p>
