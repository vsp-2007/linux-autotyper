import os
import subprocess
from typing import Optional, Literal


def detect_session_type() -> Literal["wayland", "x11", "unknown"]:
    """Detect if we're running on Wayland, X11, or unknown."""
    session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if session_type in ("wayland", "x11"):
        return session_type
    
    # Fallback checks
    if os.environ.get("WAYLAND_DISPLAY"):
        return "wayland"
    if os.environ.get("DISPLAY"):
        return "x11"
    
    return "unknown"


def is_wayland() -> bool:
    return detect_session_type() == "wayland"


def is_x11() -> bool:
    return detect_session_type() == "x11"


def detect_compositor() -> Optional[str]:
    """Try to detect the Wayland compositor or X11 window manager."""
    # Wayland compositors
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    session = os.environ.get("XDG_SESSION_DESKTOP", "").lower()
    
    known_compositors = {
        "gnome": ["gnome", "gnome-classic"],
        "kde": ["kde", "plasma"],
        "sway": ["sway"],
        "hyprland": ["hyprland"],
        "wayfire": ["wayfire"],
        "river": ["river"],
        "niri": ["niri"],
        "labwc": ["labwc"],
        "hikari": ["hikari"],
        "dwl": ["dwl"],
        "cage": ["cage"],
    }
    
    for name, identifiers in known_compositors.items():
        for identifier in identifiers:
            if identifier in desktop or identifier in session:
                return name
    
    # Check WAYLAND_DISPLAY for clues
    wl_display = os.environ.get("WAYLAND_DISPLAY", "")
    if wl_display:
        # Often format is wayland-0, wayland-1 etc.
        return "wayland-generic"
    
    # X11 window managers
    if is_x11():
        wm = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
        if wm:
            return f"x11:{wm}"
        return "x11:unknown"
    
    return None


def get_backend_priority() -> list[str]:
    """Return backend priority order based on detected session."""
    session = detect_session_type()
    compositor = detect_compositor()
    
    if session == "wayland":
        # wlroots compositors prefer wtype
        wlroots = ["sway", "hyprland", "wayfire", "river", "niri", "labwc", "hikari"]
        if compositor and any(c in compositor for c in wlroots):
            return ["wtype", "ydotool", "pynput"]
        # GNOME/KDE prefer ydotool
        if compositor in ("gnome", "kde"):
            return ["ydotool", "pynput"]
        return ["ydotool", "wtype", "pynput"]
    
    if session == "x11":
        return ["xdotool", "ydotool", "pynput"]
    
    return ["ydotool", "xdotool", "pynput", "wtype"]