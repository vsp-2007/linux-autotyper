import sys
import threading
import time
import atexit
from typing import Optional, Callable

try:
    import termios
    import tty
    HAS_TERMIOS = True
except ImportError:
    HAS_TERMIOS = False

try:
    import msvcrt
    HAS_MSVCRT = True
except ImportError:
    HAS_MSVCRT = False

try:
    from pynput import keyboard, mouse
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False


class InteractiveController:
    """
    Manages interactive typing session with:
    - Raw-mode stdin polling for 'a' (accelerate) / 'd' (decelerate)
    - pynput listener for external key/mouse detection (excludes self-typed keys)
    - Pause/resume/terminate logic
    - 10s timeout auto-resume
    """
    
    RESUME_TIMEOUT = 10.0  # seconds
    STEP_MS = 20
    MAX_EXTERNAL_EVENTS = 2  # per pause incident
    
    def __init__(
        self,
        delay_min: int,
        delay_max: int,
        on_pause: Optional[Callable[[str], None]] = None,
        on_resume: Optional[Callable[[], None]] = None,
        on_terminate: Optional[Callable[[], None]] = None,
    ):
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.on_pause = on_pause
        self.on_resume = on_resume
        self.on_terminate = on_terminate
        
        self._lock = threading.Lock()
        self._paused = False
        self._terminate = False
        self._external_count = 0
        self._last_activity_time = time.time()
        self._pause_reason = ""
        
        self._stdin_thread: Optional[threading.Thread] = None
        self._keyboard_listener = None
        self._mouse_listener = None
        self._running = False
        
        # Pynput self-typing gate
        self._self_typing = False
        
        # Terminal raw mode state
        self._orig_termios = None
        self._stdin_fd = sys.stdin.fileno() if hasattr(sys.stdin, 'fileno') else None
    
    def start(self):
        """Start stdin polling and pynput listeners."""
        if not sys.stdin.isatty():
            return  # No interactive mode for piped input
        
        self._running = True
        self._last_activity_time = time.time()
        
        # Enable raw mode for stdin (per-keystroke without Enter)
        self._enable_raw_mode()
        
        # Register atexit handler to restore terminal on abnormal exit
        atexit.register(self._disable_raw_mode)
        
        # Stdin polling thread
        self._stdin_thread = threading.Thread(target=self._poll_stdin, daemon=True)
        self._stdin_thread.start()
        
        # External activity listeners (if pynput available)
        if PYNPUT_AVAILABLE:
            self._keyboard_listener = keyboard.Listener(on_press=self._on_external_key)
            self._mouse_listener = mouse.Listener(on_click=self._on_external_click)
            self._keyboard_listener.start()
            self._mouse_listener.start()
    
    def stop(self):
        """Stop all listeners and restore terminal."""
        self._running = False
        self._disable_raw_mode()
        
        if self._keyboard_listener:
            self._keyboard_listener.stop()
        if self._mouse_listener:
            self._mouse_listener.stop()
    
    def set_self_typing(self, typing: bool):
        """Called by backend when actively typing (pynput backend)."""
        with self._lock:
            self._self_typing = typing
    
    def _enable_raw_mode(self):
        """Set terminal to raw/cbreak mode for per-keystroke input."""
        if self._stdin_fd is None:
            return
        if HAS_TERMIOS:
            try:
                self._orig_termios = termios.tcgetattr(self._stdin_fd)
                tty.setcbreak(self._stdin_fd)
            except Exception:
                pass  # Fall back to line-buffered
        elif HAS_MSVCRT:
            # Windows: msvcrt.getch() works without raw mode setup
            pass
    
    def _disable_raw_mode(self):
        """Restore terminal to original mode."""
        if self._stdin_fd is None or self._orig_termios is None:
            return
        if HAS_TERMIOS:
            try:
                termios.tcsetattr(self._stdin_fd, termios.TCSADRAIN, self._orig_termios)
            except Exception:
                pass
        self._orig_termios = None
    
    def _poll_stdin(self):
        """Poll stdin for 'a'/'d' keys (non-blocking, raw mode)."""
        import select
        
        while self._running:
            try:
                if HAS_TERMIOS:
                    # Unix: select on sys.stdin
                    ready, _, _ = select.select([sys.stdin], [], [], 0.1)
                    if ready:
                        ch = sys.stdin.read(1)
                        if ch == 'a':
                            self._accelerate()
                        elif ch == 'd':
                            self._decelerate()
                elif HAS_MSVCRT:
                    # Windows: msvcrt.kbhit()/getch()
                    import msvcrt
                    if msvcrt.kbhit():
                        ch = msvcrt.getch()
                        # msvcrt.getch() returns bytes
                        if ch == b'a':
                            self._accelerate()
                        elif ch == b'd':
                            self._decelerate()
                    time.sleep(0.05)  # Small sleep to avoid busy loop
                else:
                    # Fallback: line-buffered (requires Enter)
                    ready, _, _ = select.select([sys.stdin], [], [], 0.1)
                    if ready:
                        ch = sys.stdin.read(1)
                        if ch == 'a':
                            self._accelerate()
                        elif ch == 'd':
                            self._decelerate()
            except Exception:
                # EOF or error - exit cleanly
                break
    
    def _accelerate(self):
        with self._lock:
            self.delay_min = max(0, self.delay_min - self.STEP_MS)
            self.delay_max = max(self.delay_min, self.delay_max - self.STEP_MS)
            dm, dM = self.delay_min, self.delay_max
            self._paused = True
            self._pause_reason = f"Accelerated: delay {dm}-{dM}ms"
            pause_cb = self.on_pause
        if pause_cb:
            pause_cb(self._pause_reason)
        self._start_resume_timer()
    
    def _decelerate(self):
        with self._lock:
            self.delay_min += self.STEP_MS
            self.delay_max += self.STEP_MS
            dm, dM = self.delay_min, self.delay_max
            self._paused = True
            self._pause_reason = f"Decelerated: delay {dm}-{dM}ms"
            pause_cb = self.on_pause
        if pause_cb:
            pause_cb(self._pause_reason)
        self._start_resume_timer()
    
    def _on_external_key(self, key):
        """Called by pynput keyboard listener for ANY external key press."""
        # Ignore if we are currently self-typing via pynput backend
        with self._lock:
            if self._self_typing:
                return
        self._external_event()
    
    def _on_external_click(self, x, y, button, pressed):
        """Called by pynput mouse listener for external click."""
        if pressed:
            self._external_event()
    
    def _external_event(self):
        """Handle external key/mouse event during typing."""
        with self._lock:
            if not self._paused:
                self._external_count = 1
                self._paused = True
                self._pause_reason = "External activity detected"
                pause_cb = self.on_pause
            else:
                self._external_count += 1
                self._pause_reason = f"External activity ({self._external_count} events)"
                pause_cb = self.on_pause
            
            if self._external_count >= self.MAX_EXTERNAL_EVENTS:
                self._terminate = True
                terminate_cb = self.on_terminate
            else:
                terminate_cb = None
        
        if pause_cb:
            pause_cb(self._pause_reason)
        if terminate_cb:
            terminate_cb()
        
        self._start_resume_timer()
    
    def _pause_with_reason(self, reason: str):
        if not self._paused:
            self._paused = True
            self._pause_reason = reason
            if self.on_pause:
                self.on_pause(reason)
    
    def _start_resume_timer(self):
        """Start 10s countdown to auto-resume."""
        self._last_activity_time = time.time()
    
    def check_resume(self) -> bool:
        """
        Call periodically from typing loop.
        Returns True if should resume typing, False if still paused/terminated.
        """
        with self._lock:
            if self._terminate:
                return False
            
            if self._paused:
                elapsed = time.time() - self._last_activity_time
                if elapsed >= self.RESUME_TIMEOUT:
                    self._paused = False
                    self._external_count = 0  # Reset per incident
                    resume_cb = self.on_resume
                else:
                    resume_cb = None
                    return False
            else:
                return True
        
        if resume_cb:
            resume_cb()
        return True
    
    def get_delays(self) -> tuple[int, int]:
        with self._lock:
            return self.delay_min, self.delay_max
    
    def is_terminated(self) -> bool:
        with self._lock:
            return self._terminate