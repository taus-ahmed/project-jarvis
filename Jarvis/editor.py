"""
Jarvis/editor.py

Safe, deterministic, English-based file editing using a local LLM.
NO filesystem access.
NO intent parsing.
Only pure text-in → text-out transformation.
"""

import requests
from typing import Optional

OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3"


# ============================================================
# CORE EDITOR
# ============================================================

def generate_edited_text(original_text: str, instruction: str) -> str:
    """
    Transform text according to an English instruction.

    Rules:
    - Only modify text that already exists.
    - Never invent new content unless explicitly instructed (e.g., "add X").
    - If the instruction cannot be applied safely, return original_text.
    - Output MUST be the full edited text, not a diff or explanation.
    """

    prompt = f"""
You are a deterministic text editor.

STRICT RULES:
- Edit ONLY the provided text.
- Do NOT invent new facts, names, or content.
- If asked to replace or remove text that does not exist, return the text unchanged.
- If asked to add text, append it logically without rewriting unrelated parts.
- Return ONLY the edited text. No explanations.

Instruction:
{instruction}

Original Text:
{original_text}

Edited Text:
""".strip()

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "options": {
            "temperature": 0.0,
            "top_p": 1.0,
        },
        "stream": False,
    }

    try:
        response = requests.post(
            OLLAMA_API_URL,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()

        data = response.json()
        edited = data.get("response", "").strip()

        # Safety fallback
        if not edited:
            return original_text

        return edited

    except Exception:
        # Absolute safety fallback
        return original_text


# ============================================================
# DIFF GENERATION (FOR PREVIEW)
# ============================================================

def generate_diff(original: str, edited: str) -> str:
    """
    Generate a simple unified diff for preview.
    No external libraries.
    """
    original_lines = original.splitlines()
    edited_lines = edited.splitlines()

    diff = []
    max_len = max(len(original_lines), len(edited_lines))

    for i in range(max_len):
        o = original_lines[i] if i < len(original_lines) else ""
        e = edited_lines[i] if i < len(edited_lines) else ""

        if o == e:
            diff.append(f"  {o}")
        else:
            if o:
                diff.append(f"- {o}")
            if e:
                diff.append(f"+ {e}")

    return "\n".join(diff)
