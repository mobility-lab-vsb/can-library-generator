import re


def format_generated_code(content: str) -> str:
    """Keep one blank line between sections and one final newline."""
    lines = (line.rstrip() for line in content.splitlines())
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip() + "\n"
