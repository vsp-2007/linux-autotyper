import subprocess
import random
import time
from typing import List
from .base import Backend


class YdotoolBackend(Backend):
    name = "ydotool"
    description = "Universal typing via ydotool (X11 + Wayland)"
    
    def is_available(self) -> bool:
        return self._check_command("ydotool") and self._check_ydotoold_running()
    
    def _check_ydotoold_running(self) -> bool:
        import os
        return os.path.exists("/dev/uinput") or os.path.exists("/var/run/ydotool.socket")
    
    def type_text(self, text: str, delay_min: int, delay_max: int) -> bool:
        delay = random.randint(delay_min, delay_max)
        try:
            proc = subprocess.run(
                ["ydotool", "type", "-d", str(delay), "--"],
                input=text,
                text=True,
                check=True,
                capture_output=True
            )
            return True
        except subprocess.CalledProcessError as e:
            print(f"ydotool error: {e.stderr if e.stderr else e}")
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
                    ["ydotool", "type", "-d", str(delay), "--"],
                    input=chunk,
                    text=True,
                    check=True,
                    capture_output=True
                )
            except subprocess.CalledProcessError as e:
                print(f"ydotool error: {e.stderr if e.stderr else e}")
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