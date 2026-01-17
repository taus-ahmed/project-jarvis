"""
Jarvis/intent_parser.py

Converts natural language commands into structured intents.
NO execution. NO filesystem access.
"""

import re
from typing import Optional, Dict, List


# ============================================================
# MULTI-STEP PARSER
# ============================================================

def parse_intents(text: str) -> List[Dict]:
    """
    Split a user message into ordered atomic intents.

    Example:
    "go to desktop and ls"
    →
    [
        {"action": "cd", "target": "desktop"},
        {"action": "ls"}
    ]
    """
    parts = re.split(r"\s+and\s+", text.strip(), flags=re.IGNORECASE)
    intents = []

    for part in parts:
        intent = parse_intent(part.strip())
        if intent:
            intents.append(intent)

    return intents


# ============================================================
# SINGLE INTENT PARSER
# ============================================================

def parse_intent(text: str) -> Optional[Dict]:
    t = text.strip().lower()

    # ---------------- LS ----------------
    if t in {"ls", "list", "list files"}:
        return {"action": "ls"}

    # ---------------- CD ----------------
    nav_match = re.match(r"^(go to|navigate to)\s+(.+)$", t)
    if nav_match:
        return {
            "action": "cd",
            "target": nav_match.group(2).strip(),
        }

    # ---------------- OPEN ----------------
    open_match = re.match(r"^open\s+(.+)$", t)
    if open_match:
        return {
            "action": "open",
            "target": open_match.group(1).strip(),
        }

    # ---------------- EDIT ----------------
    add_match = re.match(r"^(add|append)\s+(.+)$", t)
    if add_match:
        return {
            "action": "edit",
            "instruction": f"{add_match.group(1)} {add_match.group(2)}",
        }

    replace_match = re.match(
        r'^replace\s+"(.+?)"\s+with\s+"(.+?)"$',
        t,
    )
    if replace_match:
        return {
            "action": "edit",
            "instruction": f'replace "{replace_match.group(1)}" with "{replace_match.group(2)}"',
        }

    remove_match = re.match(r'^remove\s+"(.+?)"$', t)
    if remove_match:
        return {
            "action": "edit",
            "instruction": f'remove "{remove_match.group(1)}"',
        }

    return None

