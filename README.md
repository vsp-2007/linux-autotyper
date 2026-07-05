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
```

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
├── utils/
│   ├── __init__.py
│   ├── compositor.py         # X11/Wayland + compositor detection
│   ├── clipboard.py          # Clipboard abstraction
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