# Jarvis MCP Orchestrator Prompt (Reference)

This prompt is embedded in `orchestrator_mcp.py` and expresses:
- Strong general/world knowledge.
- No guessing about the local machine; always use tools for filesystem/app actions.
- Single JSON tool call when needed; plain text for general answers; clarifications in plain text.
- Few-shot examples and the tool list.

Use this file to tweak or extend the prompt without touching the code.
