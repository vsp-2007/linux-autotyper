import random
import time
from .base import Backend

try:
    from pynput.keyboard import Controller, Key
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False


class PynputBackend(Backend):
    name = "pynput"
    description = "X11 fallback via pynput (pure Python)"
    
    def is_available(self) -> bool:
        if not PYNPUT_AVAILABLE:
            return False
        import os
        return os.environ.get("XDG_SESSION_TYPE", "").lower() == "x11" or os.environ.get("DISPLAY") is not None
    
    def type_text(self, text: str, delay_min: int, delay_max: int) -> bool:
        if not PYNPUT_AVAILABLE:
            print("pynput not installed")
            return False
        
        keyboard = Controller()
        
        # Special key mapping
        special_keys = {
            '\n': Key.enter,
            '\t': Key.tab,
            '\r': Key.enter,
            '\b': Key.backspace,
        }
        
        try:
            for char in text:
                if char in special_keys:
                    keyboard.press(special_keys[char])
                    keyboard.release(special_keys[char])
                else:
                    keyboard.type(char)
                
                # Random human-like delay
                delay = random.uniform(delay_min, delay_max) / 1000.0
                time.sleep(delay)
            return True
        except Exception as e:
            print(f"pynput error: {e}")
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
        if not PYNPUT_AVAILABLE:
            print("pynput not installed")
            return False
        
        # Try to get interactive controller from parent scope for self-typing gate
        interactive = getattr(self, '_interactive_controller', None)
        
        keyboard = Controller()
        
        special_keys = {
            '\n': Key.enter,
            '\t': Key.tab,
            '\r': Key.enter,
            '\b': Key.backspace,
        }
        
        try:
            if interactive:
                interactive.set_self_typing(True)
            
            for char in text:
                # Check pause/terminate before each keystroke
                if should_pause():
                    if interactive and not interactive.wait_if_paused():
                        return False  # terminated
                    # resumed — get fresh delays
                    delay_min, delay_max = get_delays()
                
                if char in special_keys:
                    keyboard.press(special_keys[char])
                    keyboard.release(special_keys[char])
                else:
                    keyboard.type(char)
                
                # Random human-like delay with current delay bounds
                delay_min, delay_max = get_delays()
                delay = random.uniform(delay_min, delay_max) / 1000.0
                time.sleep(delay)
            
            return True
        except Exception as e:
            print(f"pynput error: {e}")
            return False
        finally:
            if interactive:
                interactive.set_self_typing(False)