from abc import ABC, abstractmethod
from typing import List, Optional
import subprocess
import shutil


class Backend(ABC):
    """Abstract base class for typing backends."""
    
    name: str = "base"
    description: str = "Base backend"
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this backend can run on the current system."""
        pass
    
    @abstractmethod
    def type_text(self, text: str, delay_min: int, delay_max: int) -> bool:
        """
        Type the given text with human-like delays.
        
        Args:
            text: Text to type
            delay_min: Minimum delay between chars (ms)
            delay_max: Maximum delay between chars (ms)
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    def _check_command(self, cmd: str) -> bool:
        """Check if a command exists in PATH."""
        return shutil.which(cmd) is not None
    
    def _run_cmd(self, cmd: List[str]) -> subprocess.CompletedProcess:
        """Run a command and return the result."""
        return subprocess.run(cmd, capture_output=True, text=True)


class BackendRegistry:
    """Registry of all available backends."""
    
    def __init__(self):
        self._backends: List[Backend] = []
    
    def register(self, backend: Backend):
        self._backends.append(backend)
    
    def get_all(self) -> List[Backend]:
        return self._backends
    
    def get_available(self) -> List[Backend]:
        return [b for b in self._backends if b.is_available()]
    
    def get_by_name(self, name: str) -> Optional[Backend]:
        for b in self._backends:
            if b.name == name:
                return b
        return None
    
    def auto_select(self) -> Optional[Backend]:
        """Auto-select the best available backend."""
        available = self.get_available()
        if not available:
            return None
        
        # Priority order: wtype (native Wayland) > xdotool (mature X11) > ydotool (universal > pynput
        priority = ["wtype", "xdotool", "ydotool", "pynput"]
        for p in priority:
            for b in available:
                if b.name == p:
                    return b
        return available[0]


registry = BackendRegistry()