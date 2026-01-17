# Jarvis/mcp_filesystem/filesystem.py

import os
from typing import Optional

from Jarvis.audit_log import log_action
from Jarvis.config import ALLOWED_ROOT, FILESYSTEM_ACCESS_SCOPE
from Jarvis.memory.vector_store import store_memory


# ============================================================
# PATH RESOLUTION (CRITICAL & SAFE)
# ============================================================

def resolve_path(path: str, base_path: Optional[str] = None) -> str:
    """
    Resolve a path relative to base_path if not absolute.
    Normalizes the result to prevent traversal attacks.
    """
    if os.path.isabs(path):
        full = os.path.abspath(path)
    elif base_path:
        full = os.path.abspath(os.path.join(base_path, path))
    else:
        full = os.path.abspath(path)

    return full


# ============================================================
# ACCESS CONTROL (HARD BOUNDARY)
# ============================================================

def _is_allowed_path(path: str) -> bool:
    """
    Enforce filesystem access rules.
    """
    if FILESYSTEM_ACCESS_SCOPE == "full":
        return True  # Explicitly unsafe mode

    absolute_path = os.path.abspath(path)
    allowed_root = os.path.abspath(ALLOWED_ROOT)

    # Ensure strict containment
    return os.path.commonpath([absolute_path, allowed_root]) == allowed_root


# ============================================================
# DIRECTORY OPERATIONS
# ============================================================

def change_directory(path: str, base_path: Optional[str] = None) -> str:
    """
    Resolve and validate a directory path.
    DOES NOT call os.chdir().
    """
    action = "change_directory"
    full_path = resolve_path(path, base_path)

    if not _is_allowed_path(full_path):
        log_action(action, full_path, "FAILED", "Access denied")
        raise PermissionError("Access denied by configuration.")

    if not os.path.exists(full_path):
        log_action(action, full_path, "FAILED", "Path does not exist")
        raise FileNotFoundError("Directory does not exist.")

    if not os.path.isdir(full_path):
        log_action(action, full_path, "FAILED", "Not a directory")
        raise NotADirectoryError("Path is not a directory.")

    log_action(action, full_path, "SUCCESS", "Directory resolved")
    return full_path


def list_directory(path: str) -> list[str]:
    action = "list_directory"
    full_path = resolve_path(path)

    if not _is_allowed_path(full_path):
        log_action(action, full_path, "FAILED", "Access denied")
        raise PermissionError("Access denied.")

    if not os.path.isdir(full_path):
        log_action(action, full_path, "FAILED", "Not a directory")
        raise NotADirectoryError("Not a directory.")

    items = os.listdir(full_path)
    log_action(action, full_path, "SUCCESS", f"items={len(items)}")
    return items


# ============================================================
# FILE OPEN (OS HANDOFF ONLY)
# ============================================================

def open_path(path: str, base_path: Optional[str] = None) -> str:
    """
    Open a file or folder using OS default app (Windows).
    """
    action = "open_path"
    full_path = resolve_path(path, base_path)

    if not _is_allowed_path(full_path):
        log_action(action, full_path, "FAILED", "Access denied")
        raise PermissionError("Access denied by configuration.")

    if not os.path.exists(full_path):
        log_action(action, full_path, "FAILED", "Path does not exist")
        raise FileNotFoundError(f"Path does not exist: {full_path}")

    os.startfile(full_path)
    log_action(action, full_path, "SUCCESS", "Opened")
    return full_path


# ============================================================
# FILE READ (TEXT ONLY)
# ============================================================

def read_file(
    path: str,
    base_path: Optional[str] = None,
    max_chars: int = 10_000,
) -> str:
    action = "read_file"
    full_path = resolve_path(path, base_path)

    if not _is_allowed_path(full_path):
        log_action(action, full_path, "FAILED", "Access denied")
        raise PermissionError("Access denied.")

    if not os.path.isfile(full_path):
        log_action(action, full_path, "FAILED", "Not a file")
        raise FileNotFoundError("File does not exist.")

    try:
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read(max_chars)
    except UnicodeDecodeError:
        log_action(action, full_path, "FAILED", "Binary file")
        raise ValueError("File is not readable text.")

    store_memory(
        f"Read {os.path.basename(full_path)}",
        {"type": "file_read", "path": full_path},
    )

    log_action(action, full_path, "SUCCESS", f"chars_read={len(content)}")
    return content


# ============================================================
# FILE WRITE (OVERWRITE)
# ============================================================

def overwrite_file(
    path: str,
    text: str,
    base_path: Optional[str] = None,
) -> None:
    action = "overwrite_file"
    full_path = resolve_path(path, base_path)

    if not _is_allowed_path(full_path):
        log_action(action, full_path, "FAILED", "Access denied")
        raise PermissionError("Access denied.")

    try:
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(text)

        store_memory(
            f"Overwrote {os.path.basename(full_path)}",
            {"type": "file_edit", "action": "overwrite", "path": full_path},
        )

        log_action(action, full_path, "SUCCESS", f"chars_written={len(text)}")

    except Exception as e:
        log_action(action, full_path, "FAILED", str(e))
        raise


# ============================================================
# FILE WRITE (APPEND)
# ============================================================

def append_to_file(
    path: str,
    text: str,
    base_path: Optional[str] = None,
) -> None:
    action = "append_to_file"
    full_path = resolve_path(path, base_path)

    if not _is_allowed_path(full_path):
        log_action(action, full_path, "FAILED", "Access denied")
        raise PermissionError("Access denied.")

    try:
        with open(full_path, "a", encoding="utf-8") as f:
            f.write(text)

        store_memory(
            f"Appended to {os.path.basename(full_path)}",
            {"type": "file_edit", "action": "append", "path": full_path},
        )

        log_action(action, full_path, "SUCCESS", f"chars_appended={len(text)}")

    except Exception as e:
        log_action(action, full_path, "FAILED", str(e))
        raise
