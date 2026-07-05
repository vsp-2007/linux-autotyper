import subprocess
import random
import time
from typing import List
from .base import Backend


class WtypeBackend(Backend):
    name = "wtype"
    description = "Native Wayland typing via wtype (wlroots compositors)"
    
    def is_available(self) -> bool:
        return self._check_command("wtype") and self._is_wlroots()
    
    def _is_wlroots(self) -> bool:
        import os
        # Check for wlroots-based compositors
        desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
        session = os.environ.get("XDG_SESSION_DESKTOP", "").lower()
        compositor = os.environ.get("WAYLAND_DISPLAY", "")
        
        wlroots_desktops = ["sway", "hyprland", "wayfire", "river", "niri", "labwc", "hikari"]
        return any(d in desktop for d in wlroots_desktops) or any(d in session for d in wlroots_desktops) or bool(compositor)
    
    def type_text(self, text: str, delay_min: int, delay_max: int) -> bool:
        # wtype reads from stdin, -d for delay (ms)
        delay = random.randint(delay_min, delay_max)
        try:
            proc = subprocess.run(
                ["wtype", "-d", str(delay), "-"],
                input=text,
                text=True,
                check=True,
                capture_output=True
            )
            return True
        except subprocess.CalledProcessError as e:
            print(f"wtype error: {e.stderr if e.stderr else e}")
            return False