"""
Central place for MCP output schemas and tool definitions.
"""

# Allowed tools and their schemas
TOOLS = {
    "list_directory": {
        "description": "List files/folders at a path.",
        "params": {"path": "Absolute path, e.g., C:\\ or F:\\projects"},
    },
    "read_file": {
        "description": "Read a text file.",
        "params": {"path": "Absolute file path."},
    },
    "write_file": {
        "description": "Create or overwrite a file with text content.",
        "params": {"path": "Absolute file path", "content": "Text content to write"},
    },
    "find_file": {
        "description": "Search for a filename across drives.",
        "params": {"filename": "Name or pattern to search."},
    },
    "move_file": {
        "description": "Move a file or folder to a destination path.",
        "params": {"source": "Existing path", "destination": "New path"},
    },
    "copy_file": {
        "description": "Copy a file or folder to a destination path.",
        "params": {"source": "Existing path", "destination": "New path"},
    },
    "create_directory": {
        "description": "Create a folder at the given path.",
        "params": {"path": "Directory path to create"},
    },
    "launch_application": {
        "description": "Launch an application by name or explicit executable path.",
        "params": {
            "app_name": "Application name, e.g., 'excel', 'chrome', 'word' (preferred)",
            "exe_path": "Optional explicit executable path",
            "args": "Optional list of args"
        },
    },
    "get_active_window": {
        "description": "Get the title and process name of the currently active window.",
        "params": {},
    },
    "read_clipboard": {
        "description": "Get text content from the Windows clipboard.",
        "params": {},
    },
}

# Unified output schemas
TOOL_SCHEMA = """
When you need a system action, respond with a single JSON object:
{"tool": "<tool_name>", "params": {"key": "value"}}
Only use tools defined in the TOOLS list. Do not include any other keys.
"""

ANSWER_SCHEMA = """
For general knowledge or social replies, respond with plain text (no JSON).
"""
