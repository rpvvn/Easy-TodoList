# Easy-TodoList

A lightweight Windows desktop floating to-do widget: always-on-desktop, translucent frosted glass, rounded cards, focused on just three things — **record / complete / clear**. Minimal and low-footprint.


> 🌐 Language: [简体中文](README.md) · **English**
---

## Positioning

- A desktop-resident floating widget that shows your to-dos at a glance, no full window needed.
- Translucent frosted (Acrylic / Blur) rounded shape that lets the wallpaper show through without blocking desktop icons.
- Dark / light themes with a soft, non-glaring look.
- Lightweight and background-resident via the system tray (no taskbar occupation).

## Features

- 🧊 Frosted glass (blur) + rounded floating panels; the blur is strictly clipped inside the rounded corners (no square leakage).
- 📌 Top info bar: app logo + dynamic "N to-dos" count + add button + settings button.
- 📝 Main panel: "All To-dos" title + inline input (Enter to add) + to-do list.
- ✅ Click a to-do row to mark it done (strikethrough + dimmed).
- ⭕ Two circular floating buttons at bottom-right: check (mark all done), cross (clear completed, executes immediately).
- ⚙️ Settings view (replaces the main content area): frosted opacity, corner radius, always-on-top, show/hide top bar, lock position, lock size, launch at startup, tray behavior, global hotkeys.
- ⌨️ Global hotkeys: summon widget / new to-do (Windows `RegisterHotKey`, no extra dependency).
- 🖱 Drag from any blank area; resize via the bottom-right grip.
- 🪟 Frameless, always-on-top, adjustable opacity / corner radius.
- 👻 Minimize to tray, launch at startup.
- 💾 Auto-saved data.

## UI structure

Two rounded floating panels inside a single window:

```
┌──────────────────────────────┐
│  [Logo] N to-dos      ＋  ⚙️  │  ← top info bar
├──────────────────────────────┤
│  All To-dos            ⚙️    │  ← main panel (gear shown only when top bar is collapsed)
│  [input: Enter to add]        │
│  ── to-do list ──             │
│                        ✓  ✕  │  ← mark all done / clear completed
└──────────────────────────────┘
```

## Quick start (from source)

Requires Python 3.10+:

```bat
cd /d <project-dir>
python -m pip install -r requirements.txt
python main.py
```

Or double-click `run.bat` (auto-checks and installs dependencies).

Launch arguments:

- `python main.py --hidden`: start hidden in the system tray only.
- `python main.py --show`: force-show the window even if "start hidden in tray" is enabled.

## Build the exe

Double-click:

```bat
build.bat
```

The script installs dependencies, generates the icon, and runs PyInstaller to produce a **no-install single-file exe**:

```text
dist\Easy-TodoList.exe
```

## GitHub Actions: auto build + auto release

Pushing a `v*` tag (e.g. `v1.0.0`) triggers `.github/workflows/build-exe.yml`:

1. Builds the exe on `windows-latest` (install deps → generate icon → PyInstaller);
2. Uploads the `Easy-TodoList-windows` artifact;
3. Extracts that version's notes from `UpdateLog.md` and writes them into the GitHub Release notes, attaching `Easy-TodoList.exe`.

To trigger manually: repo **Actions** tab → **Build Windows EXE** → **Run workflow**.

## Data location

- `%APPDATA%\Easy-TodoList\todos.json`: to-do data
- `%APPDATA%\Easy-TodoList\settings.json`: theme, topmost, locks, opacity, corner radius, hotkeys, etc.

> On first launch, data is automatically migrated from the old `%APPDATA%\MaterialTodo` directory.

## Project structure

```text
main.py              main program (UI / to-do logic / tray / autostart / blur / hotkeys)
make_icon.py         app.ico icon generator
run.bat              quick run from source
build.bat            one-click build script
Easy-TodoList.spec   PyInstaller spec
requirements.txt     dependencies
.github/workflows/   GitHub Actions auto build + auto release
README.md            Chinese documentation
README_EN.md         English documentation
UpdateLog.md         changelog (auto-synced to Release Notes)
```

## FAQ

- **No frosted effect?** Enable transparency effects in Windows 10/11.
- **Square blur outside rounded corners / gap not transparent?** The app uses DWM region blur (`DwmEnableBlurBehindWindow` + `DWM_BB_BLURREGION`) clipped strictly to the rounded panels; even on some Windows 11 builds where the legacy API is weakened, the rounded corners and transparent gap remain strictly correct.
- **Can't drag the window?** Check "Lock position (disable dragging)" in Settings.
- **Can't resize the window?** Check "Lock size (disable resizing)" in Settings.
- **Can't find the close button?** Close minimizes to the system tray; right-click the tray icon to quit.
- **Autostart fails?** The app writes `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`; security software may block it.
- **SmartScreen warning?** This is an unsigned PyInstaller build; choose "Run anyway" on first launch.

<div align="center">

##### Community Promotion [Linux.do](https://linux.do)
</div>