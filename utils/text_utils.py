import re
from typing import List


def strip_leading_indent(text: str, keep_first_line: bool = True) -> str:
    """
    Strip common leading whitespace from all lines.
    
    Args:
        text: Input text
        keep_first_line: If True, don't strip the first line (useful for code blocks)
        
    Returns:
        Text with common leading indent removed
    """
    lines = text.splitlines()
    if not lines:
        return text
    
    # Find minimum indent (excluding empty lines and optionally first line)
    start_idx = 1 if keep_first_line else 0
    indents = []
    for line in lines[start_idx:]:
        if line.strip():  # Non-empty line
            match = re.match(r'^(\s*)', line)
            if match:
                indents.append(len(match.group(1)))
    
    if not indents:
        return text
    
    min_indent = min(indents)
    if min_indent == 0:
        return text
    
    # Strip min_indent from all lines (except first if keep_first_line)
    result_lines = []
    for i, line in enumerate(lines):
        if i < start_idx:
            result_lines.append(line)
        else:
            if line.startswith(' ' * min_indent):
                result_lines.append(line[min_indent:])
            else:
                result_lines.append(line)
    
    return '\n'.join(result_lines)


def map_special_chars(text: str) -> str:
    """
    Map special characters that might need special handling for typing.
    Currently just returns text as-is - backends handle special keys.
    """
    return text


def split_lines_preserve_endings(text: str) -> List[str]:
    """Split text into lines, preserving line endings."""
    return text.splitlines(keepends=True)