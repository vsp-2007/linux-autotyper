# linux-autotyper

A cross-platform Linux auto-typer that works on **X11** and **Wayland** (GNOME, KDE Plasma, wlroots: Sway, Hyprland, Wayfire, etc.). Types clipboard/file/stdin text with human-like delays.

No baked-in keybinds — bind it yourself in your DE/compositor.

---

## Quick Start
```bash
# 1. Install deps (detects distro)
bash setup.sh

# 2. Copy text to clipboard, then run (5s to click target field)
python autotyper.py

# 3. Or type from a file
python autotyper.py --file code.py

# 4. Or pipe from stdin
echo 'hello world' | python autotyper.py --stdin
```

---

## How It Works

| Backend | Protocol | Compositors | Notes |
|---------|----------|-------------|-------|
| `xdotool` | X11 | Any X11 session | Fast, mature, needs `xdotool` pkg |
| `ydotool` | X11 + Wayland | Any (if ydotoold runs) | Needs `ydotoold` daemon, uinput access |
| `wtype` | Wayland (wlroots) | Sway, Hyprland, Wayfire, River, etc. | Native Wayland, no daemon |
| `pynput` | X11 | Any X11 | Python fallback, no system deps |

**Auto-detection** picks the best available backend for your session.

---

## Install Dependencies
```bash
bash setup.sh
```
Detects distro (apt/dnf/pacman/zypper) and installs:
- `xdotool` (X11)
- `ydotool` (universal)
- `wl-clipboard` (Wayland clipboard)
- `wtype` (wlroots Wayland)
- Python `pynput`

*If your distro isn't detected, install the above manually and run `pip install -r requirements.txt`.

---

## Usage
```
python autotyper.py [options]
```

**Options:**
| Flag | Description |
|------|-------------|
| `--backend auto|xdotool|ydotool|wtype|pynput` | Force backend (default: auto) |
| `--file PATH` | Read text from file instead of clipboard |
| `--stdin` | Read text from stdin |
| `--delay-min MS` | Min delay between chars (default: 80) |
| `--delay-max MS` | Max delay between chars (default: 200) |
| `--no-indent-strip` | Keep leading whitespace on each line |
| `--no-countdown` | Skip 5-second countdown |
| `--list-backends` | Show available backends and exit |
| `--ide` | Normalize whitespace for IDE pasting (tabs→spaces, collapse blank lines, trim trailing) |
| `--verify-correct` | **BETA** Verify typed text matches expected and auto-correct mismatches (X11 only, pynput/xdotool) |

**Examples:**
```bash
# Auto-detect, clipboard, 5s countdown
python autotyper.py

# From file, faster typing
python autotyper.py --file script.py --delay-min 30 --delay-max 80

# From stdin, no countdown
cat notes.txt | python autotyper.py --stdin --no-countdown

# Force specific backend
python autotyper.py --backend wtype

# Normalize code for IDE pasting (tabs→4 spaces, collapse blank lines, trim trailing)
python autotyper.py --file code.py --ide

# BETA: Verify and auto-correct after typing (X11 only)
python autotyper.py --verify-correct
python autotyper.py --file code.py --verify-correct
```

---

## Interactive Mode (Terminal Only)

When running with clipboard input (no `--file`, no `--stdin`) in an interactive terminal, the script enters **interactive mode**:

| Key | Action |
|-----|--------|
| `a` | Accelerate (decrease delay by 20ms) |
| `d` | Decelerate (increase delay by 20ms) |

- Pressing `a`/`d` pauses typing, prints new delay, resumes after 10s inactivity
- Any external key press or mouse click pauses typing (prints reason)
- 2+ external events during a single pause = **terminate script**
- No external activity for 10s = auto-resume

> **Note:** Only works when terminal has focus (stdin polling). Not a global hotkey.

---

## Focus Guard (Wayland Tiling WMs)

On Wayland tiling compositors (Sway, Hyprland, River, etc.), mouse hover over other windows can steal focus mid-typing. **Focus Guard** automatically:

1. Captures the target window at startup (via `swaymsg` / `hyprctl` / `xdotool`)
2. Validates focus before and after each typing chunk
3. Aborts if focus shifts away — prevents typing into wrong window

No configuration needed — activates automatically on detected tiling WMs.

---

## Verification & Auto-Correction (BETA)

**`--verify-correct`** — After typing completes, automatically verify the typed text matches what was expected and fix any discrepancies.

**How it works:**
1. **Capture** — Select all (`Ctrl+A`), copy (`Ctrl+C`) the typed content
2. **Compare** — Diff against expected text using line/character-level comparison
3. **Correct** — Navigate to each mismatch (Home → Down to line → Right to column), select wrong text (`Shift+Right`), delete, retype correct text
4. **Retry** — Up to 2 correction attempts by default

**Requirements:**
- X11 session (Wayland not supported — no key combo API)
- `pynput` (preferred) or `xdotool` installed

**Supported backends:**
- `pynput` — Full support (pure Python key control)
- `xdotool` — Full support (via subprocess)
- `ydotool` / `wtype` — NOT SUPPORTED (no key combo API)

**Usage:**
```bash
# Interactive mode with verification
python autotyper.py --verify-correct

# With file input
python autotyper.py --file code.py --verify-correct
```

> **Note:** This is a BETA feature. On unsupported platforms/backends, it prints a notice and skips gracefully without failing.

---

## Binding a Hotkey

**No keybind is baked in.** Configure in your DE/compositor:

### GNOME (Wayland/X11)
Settings → Keyboard → View and Customize Shortcuts → Custom Shortcuts → Add:
- Name: `AutoTyper`
- Command: `python /path/to/autotyper.py`
- Shortcut: `Super+V` (or your choice)

### KDE Plasma
System Settings → Shortcuts → Custom Shortcuts → Edit → New → Global Shortcut → Command/URL:
- Command: `python /path/to/autotyper.py`
- Trigger: `Meta+V`

### Sway / wlroots (config)
```
bindsym $mod+v exec python /path/to/autotyper.py
```

### Hyprland (hyprland.conf)
```
bind = SUPER, V, exec, python /path/to/autotyper.py
```

---

## Backend Requirements

| Backend | Package | Notes |
|---------|---------|-------|
| `xdotool` | `xdotool` | X11 only |
| `ydotool` | `ydotool` | Needs `ydotoold` running, user in `input` group |
| `wtype` | `wtype` | wlroots only (not GNOME/KDE Wayland) |
| `pynput` | `python3-pynput` | X11 fallback, no system deps |

**ydotool setup:**
```bash
sudo systemctl enable --now ydotoold
sudo usermod -aG input $USER
# log out/in
```

---
## Architecture
```text
linux-autotyper/
├── autotyper.py              # CLI entrypoint
├── backends/
│   ├── __init__.py
│   ├── base.py               # AbstractBackend + BackendRegistry
│   ├── xdotool.py
│   ├── ydotool.py
│   ├── wtype.py
│   └── pynput_backend.py
├── src/
│   ├── __init__.py
│   ├── interactive.py        # InteractiveController (a/d speed, pause/resume)
│   └── ide_normalizer.py     # Whitespace normalization for IDE pasting
├── utils/
│   ├── __init__.py
│   ├── compositor.py         # X11/Wayland + compositor detection
│   ├── clipboard.py          # Clipboard abstraction
│   ├── focus_guard.py        # FocusGuard for Wayland tiling WMs
│   └── text_utils.py         # Char mapping, indent strip
├── setup.sh
├── requirements.txt
└── README.md
```

---

## Compatibility

| Compositor | Protocol | Recommended Backend |
|------------|----------|---------------------|
| GNOME (Wayland) | Wayland | `ydotool` |
| KDE Plasma (Wayland) | Wayland | `ydotool` |
| Sway | Wayland (wlroots) | `wtype` |
| Hyprland | Wayland (wlroots) | `wtype` |
| Wayfire | Wayland (wlroots) | `wtype` |
| Any X11 | X11 | `xdotool` |

---

## License
MIT