"""
Optional reasoning layer for Jarvis using a local LLM via Ollama.
This module NEVER retrieves memory.
It only reasons over memory passed to it.
"""

import requests
from typing import List

OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3"

SAFE_PROMPT_TEMPLATE = """
You are Jarvis, a safe AI agent.

STRICT RULES:
- Use ONLY the memory provided below.
- Do NOT invent, assume, or infer anything.
- If the memory does not answer the question, say exactly:
  "I don't know."

MEMORY:
{memory}

QUESTION:
{question}

ANSWER:
"""


def reason_with_llm(question: str, memory_chunks: List[str]) -> str:
    """
    Reasons strictly over provided memory.
    Returns a grounded answer or 'I don't know.'
    """

    # 🚫 HARD MEMORY GATE
    if not memory_chunks:
        return "I don't know."

    memory_text = "\n- ".join(memory_chunks).strip()

    if not memory_text:
        return "I don't know."

    prompt = SAFE_PROMPT_TEMPLATE.format(
        memory=memory_text,
        question=question
    )

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "options": {
            "temperature": 0.0
        },
        "stream": False
    }

    try:
        response = requests.post(
            OLLAMA_API_URL,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        answer = data.get("response", "").strip()

        # 🚨 FINAL HALLUCINATION GUARD
        if not answer or "I don't know" in answer:
            return "I don't know."

        return answer

    except Exception:
        return "I don't know."

