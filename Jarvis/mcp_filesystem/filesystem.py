# filesystem.py

import os
import glob
import shutil
import subprocess
import json
from Jarvis.audit_log import log_action
from Jarvis.config import RESTRICTED_KEYWORDS
from Jarvis.memory.vector_store import store_memory
from Jarvis.memory.file_memory import summarize_text


def _is_restricted_path(path: str) -> bool:
    """
    Checks if the path hits a blacklisted system folder.
    More conservative: only block when the absolute path starts with a restricted keyword.
    Drive roots (e.g., F:\) are always allowed.
    """
    try:
        abs_path = os.path.abspath(path)
        norm_path = os.path.normcase(abs_path)

        # Always allow drive roots like "C:\", "D:\", "F:\"
        if len(norm_path) == 3 and norm_path.endswith(":\\"):
            return False

        for forbidden in RESTRICTED_KEYWORDS:
            norm_forbid = os.path.normcase(forbidden)
            if norm_path.startswith(norm_forbid):
                return True
        return False
    except Exception:
        return True


def _resolve_startapps_appid(token: str) -> str | None:
    """Use PowerShell Get-StartApps to locate a packaged app by name token (e.g., 'sticky', 'whatsapp')."""
    if not token:
        return None
    ps = rf"(Get-StartApps | Where-Object {{ $_.Name -like '*{token}*' }} | Select-Object -First 1 -ExpandProperty AppID)"
    try:
        result = subprocess.check_output([
            "powershell", "-NoProfile", "-Command", ps
        ], text=True, timeout=5)
        appid = result.strip()
        return appid or None
    except Exception:
        return None


def _resolve_app_executable(app_name: str) -> str | None:
    """Best-effort resolution of an application name to an executable or shortcut path without hardcoding exact paths.

    Strategy:
    1) Try PATH lookup via shutil.which
    2) Try common explicit exe names in known install dirs
    3) Fallback glob search for *token*.(exe|lnk) in common roots
    """
    if not app_name:
        return None

    name = app_name.strip().strip('"').strip("'")
    if not name:
        return None

    # Direct PATH resolution (exe)
    found = shutil.which(name)
    if found and found.lower().endswith(".exe"):
        return found

    tokens = [t for t in name.lower().replace(".", " ").split() if t]
    if not tokens:
        return None

    # Prefer the most descriptive token (use longer tokens first)
    tokens_sorted = sorted(tokens, key=len, reverse=True)
    preferred = tokens_sorted[0]

    search_roots = [
        r"C:\\Program Files",
        r"C:\\Program Files (x86)",
        os.path.expanduser(r"~\\AppData\\Local\\Programs"),
        os.path.expanduser(r"~\\AppData\\Local\\Microsoft\\WindowsApps"),
        os.path.expanduser(r"~\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu"),
        r"C:\\ProgramData\\Microsoft\\Windows\Start Menu",
    ]

    # Glob by tokens (exe or lnk), most descriptive tokens first
    for root in search_roots:
        if not os.path.exists(root):
            continue
        for token in tokens_sorted:
            lower_token = token.lower()
            if lower_token.endswith((".exe", ".lnk")):
                pattern = os.path.join(root, "**", token)
                matches = glob.glob(pattern, recursive=True)
                if matches:
                    return matches[0]
            else:
                pattern_exe = os.path.join(root, "**", f"*{token}*.exe")
                pattern_lnk = os.path.join(root, "**", f"*{token}*.lnk")
                matches = glob.glob(pattern_exe, recursive=True)
                if matches:
                    return matches[0]
                matches = glob.glob(pattern_lnk, recursive=True)
                if matches:
                    return matches[0]

    # Last resort: packaged apps via Get-StartApps
    for tok in [preferred] + tokens:
        appid = _resolve_startapps_appid(tok)
        if appid:
            return f"shell:AppsFolder\\{appid}"

    return None

# def _is_safe_path(path: str) -> bool:
#     """
#     Checks whether the given path is inside the allowed root directory.
#     """
#     absolute_path = os.path.abspath(path)
#     allowed_root = os.path.abspath(ALLOWED_ROOT)
#     return absolute_path.startswith(allowed_root)


def check_exists(path: str) -> bool:
    action = "check_exists"

    if _is_restricted_path(path):
        log_action(action, path, "FAILED", "Restricted Area")
        raise PermissionError("Access denied: This is a restricted system directory.")

    exists = os.path.exists(path)
    log_action(action, path, "SUCCESS", f"exists={exists}")
    return exists


def list_directory(path: str) -> list[str]:
    action = "list_directory"

    if _is_restricted_path(path):
        log_action(action, path, "FAILED", "Restricted Area")
        raise PermissionError("Access denied: This is a restricted system directory.")

    if not os.path.exists(path):
        log_action(action, path, "FAILED", "Path does not exist")
        raise FileNotFoundError("Path does not exist.")

    if not os.path.isdir(path):
        log_action(action, path, "FAILED", "Not a directory")
        raise NotADirectoryError("Path is not a directory.")

    result = os.listdir(path)
    log_action(action, path, "SUCCESS", f"items={len(result)}")
    return result


def move_file(source: str, destination: str) -> str:
    action = "move_file"

    if _is_restricted_path(source) or _is_restricted_path(destination):
        log_action(action, source, "FAILED", "Restricted Area")
        raise PermissionError("Access denied: Restricted system directory.")

    if not os.path.exists(source):
        log_action(action, source, "FAILED", "Source missing")
        raise FileNotFoundError(f"Source does not exist: {source}")

    dest_parent = destination if os.path.isdir(destination) else os.path.dirname(destination) or "."
    if dest_parent and not os.path.exists(dest_parent):
        os.makedirs(dest_parent, exist_ok=True)

    shutil.move(source, destination)
    log_action(action, f"{source} -> {destination}", "SUCCESS", "moved")
    return destination


def copy_file(source: str, destination: str) -> str:
    action = "copy_file"

    if _is_restricted_path(source) or _is_restricted_path(destination):
        log_action(action, source, "FAILED", "Restricted Area")
        raise PermissionError("Access denied: Restricted system directory.")

    if not os.path.isfile(source):
        log_action(action, source, "FAILED", "Source not file")
        raise FileNotFoundError(f"Source file does not exist: {source}")

    dest_parent = destination if os.path.isdir(destination) else os.path.dirname(destination) or "."
    if dest_parent and not os.path.exists(dest_parent):
        os.makedirs(dest_parent, exist_ok=True)

    shutil.copy2(source, destination)
    log_action(action, f"{source} -> {destination}", "SUCCESS", "copied")
    return destination


def create_directory(path: str) -> str:
    action = "create_directory"

    if _is_restricted_path(path):
        log_action(action, path, "FAILED", "Restricted Area")
        raise PermissionError("Access denied: Restricted system directory.")

    os.makedirs(path, exist_ok=True)
    log_action(action, path, "SUCCESS", "created")
    return path


def launch_application(exe_path: str | None = None, args: list | None = None, app_name: str | None = None) -> str:
    action = "launch_application"

    # Resolve by app name when path not provided
    if not exe_path and app_name:
        exe_path = _resolve_app_executable(app_name)

    if not exe_path:
        log_action(action, "N/A", "FAILED", "No executable resolved")
        raise FileNotFoundError("Executable not found. Provide a path or a known app name.")

    if exe_path.startswith("shell:AppsFolder\\"):
        # Packaged app: try Start-Process first, then explorer fallback so UI appears
        try:
            subprocess.check_call([
                "powershell", "-NoProfile", "-Command", f"Start-Process '{exe_path}'"
            ], timeout=8)
            log_action(action, exe_path, "SUCCESS", "started packaged app via Start-Process")
            return "launched"
        except Exception as e1:
            log_action(action, exe_path, "INFO", f"Start-Process fallback to explorer: {e1}")
            try:
                subprocess.check_call(["explorer.exe", exe_path], timeout=8)
                log_action(action, exe_path, "SUCCESS", "started packaged app via explorer")
                return "launched"
            except Exception as e2:
                log_action(action, exe_path, "FAILED", f"explorer launch failed: {e2}")
                raise

    if _is_restricted_path(exe_path):
        log_action(action, exe_path, "FAILED", "Restricted Area")
        raise PermissionError("Access denied: Restricted system directory.")

    if not os.path.isfile(exe_path):
        log_action(action, exe_path, "FAILED", "Executable missing")
        raise FileNotFoundError("Executable not found.")

    ext = exe_path.lower()
    # Allow .exe via subprocess, allow .lnk via os.startfile
    if ext.endswith(".exe"):
        cmd = [exe_path] + (args or [])
        try:
            proc = subprocess.Popen(cmd, shell=False)
            log_action(action, exe_path, "SUCCESS", f"pid={proc.pid}")
            return f"launched (pid={proc.pid})"
        except Exception as e:
            log_action(action, exe_path, "FAILED", str(e))
            raise
    elif ext.endswith(".lnk"):
        try:
            os.startfile(exe_path)
            log_action(action, exe_path, "SUCCESS", "started via shortcut")
            return "launched"
        except Exception as e:
            log_action(action, exe_path, "FAILED", str(e))
            raise
    else:
        log_action(action, exe_path, "FAILED", "Unsupported extension")
        raise ValueError("Only .exe or .lnk files can be launched.")


def read_file(path: str, max_chars: int = 10_000) -> str:
    action = "read_file"

    if _is_restricted_path(path):
        log_action(action, path, "FAILED", "Restricted Area")
        raise PermissionError("Access denied: This is a restricted system directory.")

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

    if _is_restricted_path(path):
        log_action(action, path, "FAILED", "Restricted Area")
        raise PermissionError("Access denied: This is a restricted system directory.")

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


def find_file(filename: str, search_roots: list = None) -> list:
    """
    Recursively search for a file by name across the system, with sane defaults to avoid deep noise.
    Returns a list of matching file paths.
    
    Args:
        filename: The filename to search for (supports glob patterns).
        search_roots: Optional list of root directories. Defaults to ["F:/", "D:/", "C:/"].
    """
    action = "find_file"
    
    if search_roots is None:
        search_roots = ["F:/", "D:/", "C:/"]
    
    matches = []
    
    for root in search_roots:
        # Skip if root is restricted
        if _is_restricted_path(root):
            continue
        
        if not os.path.exists(root):
            continue
        
        try:
            # Build glob pattern
            pattern = os.path.join(root, "**", filename)
            found = glob.glob(pattern, recursive=True)
            
            # Filter out unwanted directories / noise
            def _ok(path_str: str) -> bool:
                low = path_str.lower()
                noisy = [
                    "venv", ".venv", "env", "envs", "site-packages", "dist-packages",
                    "__pycache__", "node_modules", "$recycle", "appdata", "windows",
                    "program files", "program files (x86)"
                ]
                if any(n in low for n in noisy):
                    return False
                return not _is_restricted_path(path_str)

            filtered = [f for f in found if _ok(f)]
            matches.extend(filtered)
        except Exception as e:
            log_action(action, root, "SKIPPED", str(e))
            continue
    
    # Remove duplicates while preserving order
    unique_matches = []
    seen = set()
    for m in matches:
        m_norm = os.path.normpath(m).lower()
        if m_norm not in seen:
            seen.add(m_norm)
            unique_matches.append(m)
    
    log_action(action, filename, "SUCCESS", f"found={len(unique_matches)}")
    return unique_matches


def write_file(path: str, content: str) -> str:
    """
    Create or overwrite a file with the given text content.
    Creates parent directories if they don't exist.
    """
    action = "write_file"

    if _is_restricted_path(path):
        log_action(action, path, "FAILED", "Restricted Area")
        raise PermissionError("Access denied: Restricted system directory.")

    parent_dir = os.path.dirname(path)
    if parent_dir and not os.path.exists(parent_dir):
        os.makedirs(parent_dir, exist_ok=True)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

    log_action(action, path, "SUCCESS", f"bytes={len(content)}")
    return f"File written: {path}"


def get_active_window() -> dict:
    """
    Get the title and process name of the currently active window (Windows only).
    Returns dict with 'title' and 'process' keys.
    """
    action = "get_active_window"
    
    try:
        import win32gui
        import win32process
        import psutil
        
        # Get foreground window
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            log_action(action, "N/A", "FAILED", "No active window")
            return {"title": None, "process": None}
        
        # Get window title
        title = win32gui.GetWindowText(hwnd)
        
        # Get process ID and name
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        try:
            process = psutil.Process(pid)
            process_name = process.name()
        except:
            process_name = "Unknown"
        
        log_action(action, process_name, "SUCCESS", f"title={title[:50]}")
        return {"title": title, "process": process_name, "pid": pid}
    
    except ImportError:
        log_action(action, "N/A", "FAILED", "Missing dependencies: pywin32, psutil")
        return {"error": "Install pywin32 and psutil: pip install pywin32 psutil"}
    except Exception as e:
        log_action(action, "N/A", "FAILED", str(e))
        return {"error": str(e)}


def read_clipboard() -> str:
    """
    Get text content from the Windows clipboard.
    """
    action = "read_clipboard"
    
    try:
        import win32clipboard
        
        win32clipboard.OpenClipboard()
        try:
            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                data = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                log_action(action, "clipboard", "SUCCESS", f"chars={len(data)}")
                return data
            else:
                log_action(action, "clipboard", "FAILED", "No text in clipboard")
                return "No text content in clipboard"
        finally:
            win32clipboard.CloseClipboard()
    
    except ImportError:
        log_action(action, "clipboard", "FAILED", "Missing pywin32")
        return "Install pywin32: pip install pywin32"
    except Exception as e:
        log_action(action, "clipboard", "FAILED", str(e))
        return f"Error reading clipboard: {e}"
