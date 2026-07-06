"""
FocusGuard — Wayland tiling WM focus stability detection.

Detects active window before typing and validates focus hasn't shifted.
Supports: Sway (swaymsg), Hyprland (hyprctl), X11 (xdotool/xprop).
"""

import subprocess
import shutil
import time
import os
from typing import Optional, Callable
from dataclasses import dataclass


@dataclass
class WindowInfo:
    window_id: str
    title: str = ""
    class_name: str = ""
    app_id: str = ""


class FocusGuard:
    """
    Monitors active window stability for Wayland tiling WMs and X11.
    
    Usage:
        guard = FocusGuard()
        if guard.available:
            guard.capture_initial()
            # ... during typing loop ...
            if not guard.check():
                print("Focus lost!")
    """
    
    def __init__(self):
        self._initial_window: Optional[WindowInfo] = None
        self._detector: Optional[Callable[[], Optional[WindowInfo]]] = None
        self._available = False
        self._init_detector()
    
    @property
    def available(self) -> bool:
        return self._available
    
    def _init_detector(self):
        """Detect and bind the best available focus query method."""
        # Wayland tiling WMs
        if shutil.which("swaymsg"):
            self._detector = self._get_sway_window
            self._available = True
        elif shutil.which("hyprctl"):
            self._detector = self._get_hyprland_window
            self._available = True
        # X11 fallback
        elif shutil.which("xdotool") and shutil.which("xprop"):
            self._detector = self._get_x11_window
            self._available = True
        elif shutil.which("xdotool"):
            self._detector = self._get_x11_window_simple
            self._available = True
        else:
            self._detector = None
            self._available = False
    
    def capture_initial(self) -> bool:
        """Capture the currently focused window as reference."""
        if not self._detector:
            return False
        self._initial_window = self._detector()
        return self._initial_window is not None
    
    def check(self) -> bool:
        """Check if focus is still on the originally captured window."""
        if not self._detector or not self._initial_window:
            return True  # No guard = assume stable
        
        current = self._detector()
        if not current:
            return True  # Can't detect = assume stable
        
        return current.window_id == self._initial_window.window_id
    
    def get_current_info(self) -> Optional[WindowInfo]:
        """Get current active window info."""
        if not self._detector:
            return None
        return self._detector()
    
    def get_initial_info(self) -> Optional[WindowInfo]:
        """Get the captured initial window info."""
        return self._initial_window
    
    # --- Detector implementations ---
    
    def _get_sway_window(self) -> Optional[WindowInfo]:
        """Get active window from swaymsg."""
        try:
            result = subprocess.run(
                ["swaymsg", "-t", "get_tree"],
                capture_output=True,
                text=True,
                timeout=1.0
            )
            if result.returncode != 0:
                return None
            
            import json
            tree = json.loads(result.stdout)
            return self._find_focused_sway(tree)
        except Exception:
            return None
    
    def _find_focused_sway(self, node) -> Optional[WindowInfo]:
        """Recursively find focused node in sway tree."""
        if node.get("focused"):
            return WindowInfo(
                window_id=str(node.get("id", "")),
                title=node.get("name", "") or "",
                class_name=node.get("window_properties", {}).get("class", "") or "",
                app_id=node.get("app_id", "") or "",
            )
        for child in node.get("nodes", []) + node.get("floating_nodes", []):
            found = self._find_focused_sway(child)
            if found:
                return found
        return None
    
    def _get_hyprland_window(self) -> Optional[WindowInfo]:
        """Get active window from hyprctl."""
        try:
            result = subprocess.run(
                ["hyprctl", "activewindow", "-j"],
                capture_output=True,
                text=True,
                timeout=1.0
            )
            if result.returncode != 0:
                return None
            
            import json
            data = json.loads(result.stdout)
            if not data.get("address"):
                return None
            
            return WindowInfo(
                window_id=data["address"],
                title=data.get("title", "") or "",
                class_name=data.get("class", "") or "",
                app_id=data.get("initialClass", "") or "",
            )
        except Exception:
            return None
    
    def _get_x11_window(self) -> Optional[WindowInfo]:
        """Get active window from xdotool + xprop (detailed)."""
        try:
            # Get window ID
            id_result = subprocess.run(
                ["xdotool", "getactivewindow"],
                capture_output=True,
                text=True,
                timeout=1.0
            )
            if id_result.returncode != 0:
                return None
            
            window_id = id_result.stdout.strip()
            
            # Get title and class via xprop
            prop_result = subprocess.run(
                ["xprop", "-id", window_id, "WM_NAME", "WM_CLASS"],
                capture_output=True,
                text=True,
                timeout=1.0
            )
            
            title = ""
            class_name = ""
            if prop_result.returncode == 0:
                for line in prop_result.stdout.splitlines():
                    if "WM_NAME" in line:
                        title = line.split("=", 1)[1].strip().strip('"')
                    elif "WM_CLASS" in line:
                        class_name = line.split("=", 1)[1].strip().split(",")[0].strip().strip('"')
            
            return WindowInfo(
                window_id=window_id,
                title=title,
                class_name=class_name,
            )
        except Exception:
            return None
    
    def _get_x11_window_simple(self) -> Optional[WindowInfo]:
        """Get active window from xdotool only (no xprop)."""
        try:
            result = subprocess.run(
                ["xdotool", "getactivewindow"],
                capture_output=True,
                text=True,
                timeout=1.0
            )
            if result.returncode != 0:
                return None
            
            return WindowInfo(window_id=result.stdout.strip())
        except Exception:
            return None


def is_tiling_wm() -> bool:
    """Detect if running on a known tiling Wayland compositor."""
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    session = os.environ.get("XDG_SESSION_DESKTOP", "").lower()
    
    tiling_wms = ["sway", "hyprland", "wayfire", "river", "niri", "labwc", "hikari", "dwl"]
    return any(wm in desktop for wm in tiling_wms) or any(wm in session for wm in tiling_wms)


def should_use_focus_guard() -> bool:
    """Determine if FocusGuard should be activated."""
    # Only on Wayland tiling WMs
    if not os.environ.get("WAYLAND_DISPLAY"):
        return False
    return is_tiling_wm()