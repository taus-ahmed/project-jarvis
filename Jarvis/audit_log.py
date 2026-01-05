# audit_log.py

import datetime
import os
from Jarvis.config import ALLOWED_ROOT

LOG_FILE = os.path.join(ALLOWED_ROOT, "jarvis_audit.log")


def log_action(action: str, path: str, status: str, message: str = "") -> None:
    """
    Writes a structured audit log entry.

    action  : name of the operation (e.g., read_file)
    path    : target path
    status  : SUCCESS / FAILED
    message : optional error or info
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_line = (
        f"[{timestamp}] "
        f"ACTION={action} "
        f"PATH={path} "
        f"STATUS={status} "
        f"MESSAGE={message}\n"
    )

    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_line)
    except Exception:
        # Logging must never crash the main flow
        pass
