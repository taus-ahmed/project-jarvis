import os
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

from Jarvis.intent_parser import parse_intents
from Jarvis.mcp_filesystem.filesystem import (
    open_path,
    read_file,
    list_directory,
    change_directory,
)
from Jarvis.input_provider import TextInputProvider, VoiceInputProvider


# ============================================================
# CONFIG
# ============================================================

EDITABLE_TEXT_EXTENSIONS = {
    ".txt", ".md", ".py", ".json", ".yaml", ".yml",
    ".csv", ".log", ".ini"
}


# ============================================================
# VOICE NORMALIZATION (CRITICAL FIX)
# ============================================================

def normalize_voice_input(text: str) -> str:
    text = text.lower().strip()

    replacements = {
        # Drive normalization
        "c drive": "cdrive",
        "see drive": "cdrive",
        "seedrive": "cdrive",
        "c derive": "cdrive",
        "see": "c",
        "c colon": "c:",

        # Folder phrases
        "downloads folder": "downloads",
        "download folder": "downloads",
        "download": "downloads",
        "desktop folder": "desktop",

        # Politeness / filler
        "please": "",
        "can you": "",
        "could you": "",
        "i want you to": "",
    }

    for k, v in replacements.items():
        if k in text:
            text = text.replace(k, v)

    return " ".join(text.split())


# ============================================================
# CONTEXT
# ============================================================

@dataclass
class ExecutionContext:
    current_working_directory: str
    last_opened_file: Optional[str] = None


# ============================================================
# HELPERS
# ============================================================

def fuzzy_find(target: str, directory: str) -> list[str]:
    try:
        target = target.lower()
        return [f for f in os.listdir(directory) if target in f.lower()]
    except Exception:
        return []


def choose_from_matches(matches: list[str]) -> Optional[str]:
    print("❓ Multiple matches found:")
    for i, m in enumerate(matches, 1):
        print(f"  {i}. {m}")

    choice = input("Choose a number: ").strip()
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(matches):
            return matches[idx]

    print("❌ Invalid selection.")
    return None


# ============================================================
# MAIN LOOP
# ============================================================

def start_chat():
    home_dir = os.path.expanduser("~")
    context = ExecutionContext(current_working_directory=home_dir)

    text_input = TextInputProvider()
    voice_input = VoiceInputProvider()
    input_provider = text_input

    # ---------------- ALIASES ----------------
    aliases = {
        "desktop": os.path.join(home_dir, "Desktop"),
        "downloads": os.path.join(home_dir, "Downloads"),
        "documents": os.path.join(home_dir, "Documents"),

        # Windows roots
        "cdrive": "C:\\",
        "c": "C:\\",
        "c:": "C:\\",
        "root": "C:\\",
    }

    print("🤖 Jarvis is online.")
    print("Commands: go to <folder>, open <file>, ls")
    print("Modes: mode voice | mode text | exit\n")

    while True:
        raw_input = input_provider.get_input()
        if not raw_input:
            continue

        # ✅ THIS IS THE FIX
        user_input = normalize_voice_input(raw_input)

        # ====================================================
        # MODE SWITCH
        # ====================================================
        if user_input == "mode voice":
            input_provider = voice_input
            print("🎤 Voice mode enabled.")
            continue

        if user_input == "mode text":
            input_provider = text_input
            print("⌨️ Text mode enabled.")
            continue

        # ====================================================
        # EXIT
        # ====================================================
        if user_input == "exit":
            print("👋 Goodbye.")
            break

        # ====================================================
        # LS (HANDLE EARLY)
        # ====================================================
        if user_input == "ls":
            print(f"📂 {context.current_working_directory}:")
            try:
                for item in list_directory(context.current_working_directory):
                    print(f"  {item}")
            except Exception as e:
                print(f"❌ {e}")
            continue

        # ====================================================
        # SINGLE-WORD DIR NAV
        # ====================================================
        if user_input in aliases:
            try:
                context.current_working_directory = change_directory(
                    aliases[user_input],
                    context.current_working_directory
                )
                print(f"📁 Changed directory to: {context.current_working_directory}")
            except Exception as e:
                print(f"❌ {e}")
            continue

        # ====================================================
        # MULTI-STEP COMMANDS
        # ====================================================
        intents = parse_intents(user_input)
        if intents:
            for intent in intents:
                action = intent.get("action")
                target = intent.get("target", "").lower()
                resolved = aliases.get(target, target)

                # ---------- CD ----------
                if action == "cd":
                    try:
                        context.current_working_directory = change_directory(
                            resolved,
                            context.current_working_directory
                        )
                        print(f"📁 Changed directory to: {context.current_working_directory}")
                    except Exception as e:
                        print(f"❌ {e}")
                    continue

                # ---------- OPEN ----------
                if action == "open":
                    matches = fuzzy_find(target, context.current_working_directory)
                    if not matches:
                        print("❌ No match found.")
                        break

                    chosen = matches[0] if len(matches) == 1 else choose_from_matches(matches)
                    if not chosen:
                        break

                    context.last_opened_file = open_path(
                        chosen,
                        context.current_working_directory
                    )
                    print(f"📂 Opened: {chosen}")
                    continue

            continue

        # ====================================================
        # FALLBACK
        # ====================================================
        print("🤔 Jarvis: I don't know.")


if __name__ == "__main__":
    start_chat()
