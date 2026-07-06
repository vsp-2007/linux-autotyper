"""
Post-typing verification and auto-correction.

Flow:
1. After typing completes, capture current buffer (Ctrl+A, Ctrl+C)
2. Compare with expected text using diff
3. If mismatches found, navigate to each difference and retype

Supports:
- pynput (X11) — key combos via Controller
- xdotool (X11) — key combos via subprocess
- Beta feature: enabled with --verify-correct flag
"""

import time
import subprocess
import shutil
import os
import difflib
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum


class VerificationBackend(Enum):
    PYNPUT = "pynput"
    XDOTOOL = "xdotool"
    UNSUPPORTED = "unsupported"


@dataclass
class DiffRegion:
    """A region where expected and actual text differ."""
    line: int       # Line number (0-indexed)
    col: int        # Column in that line (0-indexed)
    expected: str   # What should be there
    actual: str     # What is actually there


def compute_diff(expected: str, actual: str) -> List[DiffRegion]:
    """
    Compute diff regions between expected and actual text using difflib.
    Returns list of regions that need correction, with line/col coordinates.
    """
    if expected == actual:
        return []
    
    expected_lines = expected.splitlines(keepends=True)
    actual_lines = actual.splitlines(keepends=True)
    
    # Use difflib for proper diff with insert/delete handling
    matcher = difflib.SequenceMatcher(None, expected_lines, actual_lines)
    
    diffs = []
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            continue
        
        if tag == 'replace':
            # Lines changed - compare character by character within the range
            for exp_idx, act_idx in zip(range(i1, i2), range(j1, j2)):
                exp_line = expected_lines[exp_idx]
                act_line = actual_lines[act_idx]
                if exp_line != act_line:
                    col = 0
                    while col < len(exp_line) and col < len(act_line) and exp_line[col] == act_line[col]:
                        col += 1
                    diffs.append(DiffRegion(
                        line=exp_idx,
                        col=col,
                        expected=exp_line[col:],
                        actual=act_line[col:] if col < len(act_line) else ""
                    ))
        
        elif tag == 'delete':
            # Lines deleted from expected (missing in actual)
            for exp_idx in range(i1, i2):
                diffs.append(DiffRegion(
                    line=exp_idx,
                    col=0,
                    expected=expected_lines[exp_idx],
                    actual=""
                ))
        
        elif tag == 'insert':
            # Lines inserted in actual (extra in actual)
            for act_idx in range(j1, j2):
                diffs.append(DiffRegion(
                    line=act_idx,
                    col=0,
                    expected="",
                    actual=actual_lines[act_idx]
                ))
    
    return diffs


def get_clipboard_text() -> Optional[str]:
    """Get text from clipboard using available tool."""
    for cmd in [["wl-paste", "--no-newline"], ["xclip", "-selection", "clipboard", "-o"], ["xsel", "--clipboard", "--output"]]:
        if shutil.which(cmd[0]):
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    return result.stdout
            except Exception:
                pass
    return None


def detect_verification_backend() -> VerificationBackend:
    """Detect which verification backend is available."""
    # Check X11
    is_x11 = os.environ.get("XDG_SESSION_TYPE", "").lower() == "x11" or os.environ.get("DISPLAY") is not None
    if not is_x11:
        return VerificationBackend.UNSUPPORTED
    
    # Prefer pynput (pure Python, more reliable)
    try:
        import pynput
        return VerificationBackend.PYNPUT
    except ImportError:
        pass
    
    # Fallback to xdotool
    if shutil.which("xdotool"):
        return VerificationBackend.XDOTOOL
    
    return VerificationBackend.UNSUPPORTED


def verify_and_correct(
    expected_text: str,
    max_retries: int = 2,
) -> bool:
    """
    Verify typed text matches expected, and auto-correct if needed.
    
    Args:
        expected_text: The text that should be in the field
        max_retries: Maximum correction attempts
        
    Returns:
        True if verification passed (or corrected), False on failure
    """
    backend = detect_verification_backend()
    
    if backend == VerificationBackend.UNSUPPORTED:
        print("[VERIFY] Unsupported platform/backend (need X11 + pynput or xdotool)")
        return True  # Don't fail, just skip
    
    print(f"[VERIFY] Using {backend.value} for verification...")
    
    if backend == VerificationBackend.PYNPUT:
        return _verify_and_correct_pynput(expected_text, max_retries)
    elif backend == VerificationBackend.XDOTOOL:
        return _verify_and_correct_xdotool(expected_text, max_retries)
    
    return True


def _verify_and_correct_pynput(
    expected_text: str,
    max_retries: int = 2,
) -> bool:
    """Verify and correct using pynput (X11)."""
    try:
        from pynput.keyboard import Controller, Key
    except ImportError:
        print("[VERIFY] pynput not available")
        return False
    
    keyboard = Controller()
    
    for attempt in range(max_retries + 1):
        # Select all and copy
        keyboard.press(Key.ctrl_l)
        keyboard.press('a')
        keyboard.release('a')
        keyboard.release(Key.ctrl_l)
        time.sleep(0.1)
        
        keyboard.press(Key.ctrl_l)
        keyboard.press('c')
        keyboard.release('c')
        keyboard.release(Key.ctrl_l)
        time.sleep(0.15)
        
        actual_text = get_clipboard_text()
        if actual_text is None:
            print("[VERIFY] Could not read clipboard")
            return False
        
        if actual_text == expected_text:
            if attempt > 0:
                print(f"[VERIFY] Corrected successfully on attempt {attempt}")
            return True
        
        if attempt == max_retries:
            print(f"[VERIFY] Max retries reached. Text still doesn't match.")
            return False
        
        diffs = compute_diff(expected_text, actual_text)
        if not diffs:
            return True
        
        print(f"[VERIFY] Attempt {attempt + 1}: Found {len(diffs)} mismatch region(s), correcting...")
        
        for diff in diffs:
            # Navigate to line start
            keyboard.press(Key.home)
            keyboard.release(Key.home)
            time.sleep(0.05)
            
            # Move down to correct line
            for _ in range(diff.line):
                keyboard.press(Key.down)
                keyboard.release(Key.down)
                time.sleep(0.02)
            
            # Move to column
            for _ in range(diff.col):
                keyboard.press(Key.right)
                keyboard.release(Key.right)
                time.sleep(0.01)
            
            # Select the wrong text
            select_len = len(diff.actual) if diff.actual else len(diff.expected)
            for _ in range(select_len):
                keyboard.press(Key.shift)
                keyboard.press(Key.right)
                keyboard.release(Key.right)
                keyboard.release(Key.shift)
                time.sleep(0.01)
            
            # Delete and retype correct text
            keyboard.press(Key.backspace)
            keyboard.release(Key.backspace)
            time.sleep(0.05)
            
            keyboard.type(diff.expected)
            time.sleep(0.05)
        
        time.sleep(0.2)
    
    return False


def _verify_and_correct_xdotool(
    expected_text: str,
    max_retries: int = 2,
) -> bool:
    """Verify and correct using xdotool (X11)."""
    for attempt in range(max_retries + 1):
        # Select all and copy
        try:
            subprocess.run(["xdotool", "key", "ctrl+a"], check=True, capture_output=True)
            time.sleep(0.1)
            subprocess.run(["xdotool", "key", "ctrl+c"], check=True, capture_output=True)
            time.sleep(0.15)
        except subprocess.CalledProcessError:
            print("[VERIFY] xdotool key commands failed")
            return False
        
        actual_text = get_clipboard_text()
        if actual_text is None:
            print("[VERIFY] Could not read clipboard")
            return False
        
        if actual_text == expected_text:
            if attempt > 0:
                print(f"[VERIFY] Corrected successfully on attempt {attempt}")
            return True
        
        if attempt == max_retries:
            print(f"[VERIFY] Max retries reached. Text still doesn't match.")
            return False
        
        diffs = compute_diff(expected_text, actual_text)
        if not diffs:
            return True
        
        print(f"[VERIFY] Attempt {attempt + 1}: Found {len(diffs)} mismatch region(s), correcting...")
        
        for diff in diffs:
            # Navigate to line start
            subprocess.run(["xdotool", "key", "Home"], check=True)
            time.sleep(0.05)
            
            # Move down to correct line
            for _ in range(diff.line):
                subprocess.run(["xdotool", "key", "Down"], check=True)
                time.sleep(0.02)
            
            # Move to column
            for _ in range(diff.col):
                subprocess.run(["xdotool", "key", "Right"], check=True)
                time.sleep(0.01)
            
            # Select wrong text
            select_len = len(diff.actual) if diff.actual else len(diff.expected)
            for _ in range(select_len):
                subprocess.run(["xdotool", "key", "shift+Right"], check=True)
                time.sleep(0.01)
            
            # Delete and retype
            subprocess.run(["xdotool", "key", "BackSpace"], check=True)
            time.sleep(0.05)
            subprocess.run(["xdotool", "type", "--delay", "10", "--", diff.expected], check=True)
            time.sleep(0.05)
        
        time.sleep(0.2)
    
    return False