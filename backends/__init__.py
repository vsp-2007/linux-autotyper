# Backends package

from .base import Backend, BackendRegistry, registry
from .xdotool import XdotoolBackend
from .ydotool import YdotoolBackend
from .wtype import WtypeBackend
from .pynput_backend import PynputBackend

# Register all backends
registry.register(XdotoolBackend())
registry.register(YdotoolBackend())
registry.register(WtypeBackend())
registry.register(PynputBackend())

__all__ = [
    "Backend",
    "BackendRegistry", 
    "registry",
    "XdotoolBackend",
    "YdotoolBackend",
    "WtypeBackend",
    "PynputBackend",
]