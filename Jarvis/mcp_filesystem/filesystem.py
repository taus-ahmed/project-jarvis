# filesystem.py

import os
from Jarvis.audit_log import log_action
from Jarvis.config import ALLOWED_ROOT
from Jarvis.memory.vector_store import store_memory
from Jarvis.memory.file_memory import summarize_text


def _is_safe_path(path: str) -> bool:
    """
    Checks whether the given path is inside the allowed root directory.
    """
    absolute_path = os.path.abspath(path)
    allowed_root = os.path.abspath(ALLOWED_ROOT)
    return absolute_path.startswith(allowed_root)


def check_exists(path: str) -> bool:
    action = "check_exists"

    if not _is_safe_path(path):
        log_action(action, path, "FAILED", "Outside allowed root")
        raise PermissionError("Access denied: Path is outside allowed root.")

    exists = os.path.exists(path)
    log_action(action, path, "SUCCESS", f"exists={exists}")
    return exists


def list_directory(path: str) -> list[str]:
    action = "list_directory"

    if not _is_safe_path(path):
        log_action(action, path, "FAILED", "Outside allowed root")
        raise PermissionError("Access denied: Path is outside allowed root.")

    if not os.path.exists(path):
        log_action(action, path, "FAILED", "Path does not exist")
        raise FileNotFoundError("Path does not exist.")

    if not os.path.isdir(path):
        log_action(action, path, "FAILED", "Not a directory")
        raise NotADirectoryError("Path is not a directory.")

    result = os.listdir(path)
    log_action(action, path, "SUCCESS", f"items={len(result)}")
    return result


def read_file(path: str, max_chars: int = 10_000) -> str:
    action = "read_file"

    if not _is_safe_path(path):
        log_action(action, path, "FAILED", "Outside allowed root")
        raise PermissionError("Access denied: Path is outside allowed root.")

    if not os.path.exists(path):
        log_action(action, path, "FAILED", "File does not exist")
        raise FileNotFoundError("File does not exist.")

    if not os.path.isfile(path):
        log_action(action, path, "FAILED", "Not a file")
        raise IsADirectoryError("Path is not a file.")

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read(max_chars)
    except UnicodeDecodeError:
        log_action(action, path, "FAILED", "Binary or non-text file")
        raise ValueError("File is not a readable text file.")

    # 🔥 AUTO FILE MEMORY (DEMO-GRADE)
    summary = summarize_text(content)

    store_memory(
        summary,
        {
            "type": "file_summary",
            "path": path,
            "filename": os.path.basename(path)
        }
    )

    log_action(action, path, "SUCCESS", f"chars_read={len(content)}")
    return content


def read_file_stream(path: str, offset: int = 0, length: int = 1024) -> str:
    """
    Safely reads a chunk of a text file starting from a given offset.

    offset : byte position to start reading from
    length : number of characters to read
    """
    action = "read_file_stream"

    if not _is_safe_path(path):
        log_action(action, path, "FAILED", "Outside allowed root")
        raise PermissionError("Access denied: Path is outside allowed root.")

    if not os.path.exists(path):
        log_action(action, path, "FAILED", "File does not exist")
        raise FileNotFoundError("File does not exist.")

    if not os.path.isfile(path):
        log_action(action, path, "FAILED", "Not a file")
        raise IsADirectoryError("Path is not a file.")

    if offset < 0 or length <= 0:
        log_action(action, path, "FAILED", "Invalid offset/length")
        raise ValueError("Invalid offset or length.")

    try:
        with open(path, "r", encoding="utf-8") as f:
            f.seek(offset)
            chunk = f.read(length)
    except UnicodeDecodeError:
        log_action(action, path, "FAILED", "Binary or non-text file")
        raise ValueError("File is not a readable text file.")

    log_action(
        action,
        path,
        "SUCCESS",
        f"offset={offset}, length={len(chunk)}"
    )

    return chunk
