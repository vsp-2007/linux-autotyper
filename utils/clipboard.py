import os
import subprocess
import shutil
from typing import Optional


def get_clipboard_text() -> Optional[str]:
    """Get text from clipboard using the best available method."""
    session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
    
    # Wayland: prefer wl-paste
    if session_type == "wayland" or os.environ.get("WAYLAND_DISPLAY"):
        if shutil.which("wl-paste"):
            try:
                result = subprocess.run(
                    ["wl-paste", "--no-newline"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    return result.stdout
            except Exception:
                pass
    
    # X11: try xclip, then xsel
    if session_type == "x11" or os.environ.get("DISPLAY"):
        for cmd in [["xclip", "-selection", "clipboard", "-o"], ["xsel", "--clipboard", "--output"]]:
            if shutil.which(cmd[0]):
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
                    if result.returncode == 0:
                        return result.stdout
                except Exception:
                    pass
    
    # Fallback: try both anyway (some Wayland sessions have xclip via XWayland)
    for cmd in [["wl-paste", "--no-newline"], ["xclip", "-selection", "clipboard", "-o"], ["xsel", "--clipboard", "--output"]]:
        if shutil.which(cmd[0]):
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    return result.stdout
            except Exception:
                pass
    
    return None