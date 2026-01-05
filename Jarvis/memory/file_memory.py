# Jarvis/memory/file_memory.py

def summarize_text(text: str, max_lines: int = 5) -> str:
    """
    Create a simple, deterministic summary of a text file.
    """
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    summary_lines = lines[:max_lines]
    return " ".join(summary_lines)

