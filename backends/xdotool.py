import subprocess
import random
import time
from typing import List
from .base import Backend


class XdotoolBackend(Backend):
    name = "xdotool"
    description = "X11 typing via xdotool"
    
    def is_available(self) -> bool:
        return self._check_command("xdotool") and self._is_x11()
    
    def _is_x11(self) -> bool:
        import os
        return os.environ.get("XDG_SESSION_TYPE", "").lower() == "x11" or os.environ.get("DISPLAY") is not None
    
    def type_text(self, text: str, delay_min: int, delay_max: int) -> bool:
        # xdotool types directly with --delay (in ms)
        # Use random delay between min/max per char
        delay = random.randint(delay_min, delay_max)
        try:
            subprocess.run(
                ["xdotool", "type", "--delay", str(delay), "--", text],
                check=True,
                capture_output=True
            )
            return True
        except subprocess.CalledProcessError as e:
            print(f"xdotool error: {e.stderr.decode() if e.stderr else e}")
            return False