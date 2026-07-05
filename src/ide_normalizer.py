def normalize_for_ide(text: str) -> str:
    """
    Normalize text for IDE pasting:
    - Convert tabs to 4 spaces
    - Strip trailing whitespace from each line
    - Collapse multiple consecutive blank lines to single blank line
    - Strip common leading indent (preserve first line)
    """
    lines = text.splitlines()
    
    # Tab → 4 spaces
    lines = [line.replace('\t', '    ') for line in lines]
    
    # Trim trailing whitespace
    lines = [line.rstrip() for line in lines]
    
    # Collapse multiple blank lines
    result = []
    prev_blank = False
    for line in lines:
        is_blank = (line.strip() == '')
        if is_blank and prev_blank:
            continue
        result.append(line)
        prev_blank = is_blank
    
    # Strip common leading indent (preserve first line)
    if len(result) > 1:
        indents = []
        for line in result[1:]:
            if line.strip():
                indents.append(len(line) - len(line.lstrip()))
        if indents:
            min_indent = min(indents)
            result = [result[0]] + [
                line[min_indent:] if line.startswith(' ' * min_indent) else line
                for line in result[1:]
            ]
    
    return '\n'.join(result)