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
        desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
        session = os.environ.get("XDG_SESSION_DESKTOP", "").lower()
        compositor = os.environ.get("WAYLAND_DISPLAY", "")
        
        wlroots_desktops = ["sway", "hyprland", "wayfire", "river", "niri", "labwc", "hikari"]
        return any(d in desktop for d in wlroots_desktops) or any(d in session for d in wlroots_desktops) or bool(compositor)
    
    def type_text(self, text: str, delay_min: int, delay_max: int) -> bool:
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
    
    def type_text_interactive(
        self,
        text: str,
        delay_min: int,
        delay_max: int,
        get_delays,
        should_pause,
        check_focus=None,
    ) -> bool:
        CHUNK_SIZE = 80
        
        chunks = [text[i:i+CHUNK_SIZE] for i in range(0, len(text), CHUNK_SIZE)]
        
        for chunk in chunks:
            # Check pause before chunk
            if should_pause():
                # Wait for resume or termination
                if not self._wait_for_resume(should_pause):
                    return False  # terminated
            
            # Focus check before typing chunk
            if check_focus and not check_focus():
                print("[FOCUS LOST] Focus shifted away from target window — aborting")
                return False
            
            delay_min, delay_max = get_delays()
            delay = random.randint(delay_min, delay_max)
            
            try:
                subprocess.run(
                    ["wtype", "-d", str(delay), "-"],
                    input=chunk,
                    text=True,
                    check=True,
                    capture_output=True
                )
            except subprocess.CalledProcessError as e:
                print(f"wtype error: {e.stderr if e.stderr else e}")
                return False
            
            # Focus check after chunk
            if check_focus and not check_focus():
                print("[FOCUS LOST] Focus shifted away from target window — aborting")
                return False
        
        return True
    
    def _wait_for_resume(self, should_pause):
        """Wait for resume or termination. Returns True if resumed, False if terminated."""
        while True:
            time.sleep(0.1)
            if not should_pause():
                return True  # resumed