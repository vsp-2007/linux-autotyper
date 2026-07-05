# Utils package

from .compositor import detect_session_type, detect_compositor, is_wayland, is_x11
from .clipboard import get_clipboard_text
from .text_utils import strip_leading_indent, map_special_chars

__all__ = [
    "detect_session_type",
    "detect_compositor", 
    "is_wayland",
    "is_x11",
    "get_clipboard_text",
    "strip_leading_indent",
    "map_special_chars",
]