#!/usr/bin/env python3
"""
linux-autotyper - Cross-platform auto-typer for Linux (X11 + Wayland)

Types clipboard/file/stdin text with human-like delays.
No baked-in keybinds — bind it yourself in your DE/compositor.
"""

import argparse
import sys
import time
import random
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from backends import registry
from utils.clipboard import get_clipboard_text
from utils.text_utils import strip_leading_indent
from utils.compositor import detect_session_type, detect_compositor, get_backend_priority
from utils.focus_guard import FocusGuard, should_use_focus_guard
from src.interactive import InteractiveController
from src.ide_normalizer import normalize_for_ide


def parse_args():
    parser = argparse.ArgumentParser(
        description="Auto-type text on Linux (X11 + Wayland)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python autotyper.py                    # Type clipboard (5s countdown)
  python autotyper.py --file code.py     # Type from file
  echo "hello" | python autotyper.py --stdin  # Type from stdin
  python autotyper.py --backend wtype    # Force backend
  python autotyper.py --list-backends    # Show available backends
  python autotyper.py --ide              # Normalize whitespace for IDE pasting
        """
    )
    
    # Input source (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "--file", "-f",
        type=Path,
        help="Read text from file instead of clipboard"
    )
    input_group.add_argument(
        "--stdin",
        action="store_true",
        help="Read text from stdin"
    )
    
    # Backend selection
    parser.add_argument(
        "--backend",
        choices=["auto", "xdotool", "ydotool", "wtype", "pynput"],
        default="auto",
        help="Force specific backend (default: auto-detect)"
    )
    parser.add_argument(
        "--list-backends",
        action="store_true",
        help="List available backends and exit"
    )
    
    # Typing behavior
    parser.add_argument(
        "--delay-min",
        type=int,
        default=80,
        help="Minimum delay between chars in ms (default: 80)"
    )
    parser.add_argument(
        "--delay-max",
        type=int,
        default=200,
        help="Maximum delay between chars in ms (default: 200)"
    )
    parser.add_argument(
        "--no-indent-strip",
        action="store_true",
        help="Keep leading whitespace on each line (default: strip common indent)"
    )
    parser.add_argument(
        "--no-countdown",
        action="store_true",
        help="Skip 5-second countdown before typing"
    )
    
    # New v2 features
    parser.add_argument(
        "--ide",
        action="store_true",
        help="Normalize whitespace for IDE pasting (tabs→spaces, collapse blank lines, trim trailing)"
    )
    
    return parser.parse_args()


def get_text(args) -> str:
    """Get text from the selected source."""
    if args.file:
        try:
            return args.file.read_text(encoding="utf-8")
        except Exception as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)
    
    if args.stdin:
        text = sys.stdin.read()
        if not text:
            print("No input from stdin", file=sys.stderr)
            sys.exit(1)
        return text
    
    # Default: clipboard
    text = get_clipboard_text()
    if text is None:
        print("Could not read clipboard. Install wl-clipboard (Wayland) or xclip/xsel (X11).", file=sys.stderr)
        sys.exit(1)
    if not text:
        print("Clipboard is empty", file=sys.stderr)
        sys.exit(1)
    return text


def countdown(seconds: int = 5):
    """Show countdown before typing."""
    print(f"Typing in {seconds} seconds... (click target field)")
    for i in range(seconds, 0, -1):
        print(f"  {i}...", end="\r", flush=True)
        time.sleep(1)
    print("  GO!      ")


def main():
    args = parse_args()
    
    # Handle --list-backends
    if args.list_backends:
        print("Available backends:")
        available = registry.get_available()
        if not available:
            print("  (none)")
        for b in available:
            print(f"  - {b.name}: {b.description}")
        print(f"\nSession: {detect_session_type()}")
        print(f"Compositor: {detect_compositor() or 'unknown'}")
        print(f"Priority order: {', '.join(get_backend_priority())}")
        return
    
    # Get text to type
    text = get_text(args)
    
    # Apply --ide normalization if requested
    if args.ide:
        text = normalize_for_ide(text)
    
    # Strip leading indent unless disabled
    if not args.no_indent_strip:
        text = strip_leading_indent(text)
    
    # Select backend
    if args.backend == "auto":
        backend = registry.auto_select()
        if backend is None:
            print("No suitable backend found. Install xdotool, ydotool, wtype, or pynput.", file=sys.stderr)
            sys.exit(1)
        print(f"Auto-selected backend: {backend.name}")
    else:
        backend = registry.get_by_name(args.backend)
        if backend is None:
            print(f"Unknown backend: {args.backend}", file=sys.stderr)
            sys.exit(1)
        if not backend.is_available():
            print(f"Backend '{args.backend}' is not available on this system.", file=sys.stderr)
            sys.exit(1)
    
    # Determine if interactive mode should activate
    # Only when: TTY, clipboard input (not --file/--stdin), not --no-countdown
    use_interactive = (
        sys.stdin.isatty() and
        not args.stdin and
        not args.file
    )
    
    # Initialize InteractiveController if needed
    interactive = None
    focus_guard = None
    
    if use_interactive:
        interactive = InteractiveController(
            delay_min=args.delay_min,
            delay_max=args.delay_max,
            on_pause=lambda reason: print(f"\n[PAUSED] {reason} — resuming in {InteractiveController.RESUME_TIMEOUT:.0f}s..."),
            on_resume=lambda: print("\n[RESUMED]"),
            on_terminate=lambda: print("\n[TERMINATED] Too many external events — aborting."),
        )
        interactive.start()
        
        # Attach to pynput backend for self-typing gate
        if backend.name == "pynput":
            backend._interactive_controller = interactive
        
        # Initialize FocusGuard for Wayland tiling WMs
        if should_use_focus_guard():
            focus_guard = FocusGuard()
            if focus_guard.capture_initial():
                init_info = focus_guard.get_initial_info()
                print(f"[FOCUS GUARD] Monitoring window: {init_info.title or init_info.class_name or init_info.window_id}")
    
    # Countdown
    if not args.no_countdown:
        countdown(5)
    
    # Type!
    print(f"Typing {len(text)} chars via {backend.name}...")
    
    # Prepare callbacks for interactive mode
    get_delays = None
    should_pause = None
    check_focus = None
    
    if interactive:
        get_delays = interactive.get_delays
        should_pause = lambda: not interactive.check_resume()
        if focus_guard:
            check_focus = focus_guard.check
    
    # Call appropriate typing method
    if interactive and hasattr(backend, 'type_text_interactive'):
        success = backend.type_text_interactive(
            text,
            args.delay_min,
            args.delay_max,
            get_delays,
            should_pause,
            check_focus,
        )
    else:
        success = backend.type_text(text, args.delay_min, args.delay_max)
    
    # Cleanup
    if interactive:
        interactive.stop()
    
    if success:
        print("Done!")
    else:
        print("Failed!", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()