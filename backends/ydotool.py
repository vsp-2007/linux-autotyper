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
        # ydotool communicates via /dev/uinput or socket
        return os.path.exists("/dev/uinput") or os.path.exists("/var/run/ydotool.socket")
    
    def type_text(self, text: str, delay_min: int, delay_max: int) -> bool:
        # ydotool types from stdin with -d delay (ms)
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