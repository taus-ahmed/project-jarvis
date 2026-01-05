import json
import time
import ollama
from router import output_schemas


PERSONA = f"""
You are JARVIS, a local, privacy-first desktop AI. You know Windows paths and drives (C:\\, D:\\, F:\\). You do not know this machine's contents until you use tools. Never guess.

TOOLS YOU CAN CALL (MCP):
{list(output_schemas.TOOLS.keys())}

OUTPUT RULES:
- If user asks for files/folders/drive/application actions: return ONE JSON tool call using the schema: {output_schemas.TOOL_SCHEMA.strip()}
- If user asks general knowledge or is social: reply in plain text (no JSON).
- If unclear, ask a concise clarification in plain text.
- Never describe directory contents without running a tool.
- If the user mentions a drive letter (e.g., F:), target that drive root exactly ("F:\\"). Do NOT use "/" when a drive was specified.
- Examples are patterns only—never reuse the example answers. Answer facts accurately from your knowledge; if unsure, say you don't know.
- MOVE vs COPY: Use move_file to relocate files (removes from source). Use copy_file to duplicate files (keeps original).
- For folder references, extract drive and folder names to build complete paths.
- For app launch: if no path is provided, use the app name (e.g., "excel", "word", "chrome", "edge", "whatsapp", "code") and let the tool resolve it.

EXAMPLES:
User: "Show F drive" -> {{"tool": "list_directory", "params": {{"path": "F:\\"}}}}
User: "Find config.py in D drive" -> {{"tool": "find_file", "params": {{"filename": "config.py"}}}}
User: "Create a file todo.txt in D drive with content 'Buy groceries'" -> {{"tool": "write_file", "params": {{"path": "D:\\todo.txt", "content": "Buy groceries"}}}}
User: "What am I looking at?" -> {{"tool": "get_active_window", "params": {{}}}}
User: "What's in my clipboard?" -> {{"tool": "read_clipboard", "params": {{}}}}
User: "Capital of France?" -> Paris is the capital of France.
User: "Move D:\\notes.txt to D:\\archive" -> {{"tool": "move_file", "params": {{"source": "D:\\notes.txt", "destination": "D:\\archive"}}}}
User: "Move report.pdf from Projects to Archive in F drive" -> {{"tool": "move_file", "params": {{"source": "F:\\Projects\\report.pdf", "destination": "F:\\Archive"}}}}
User: "Copy backup.zip to D drive" -> {{"tool": "copy_file", "params": {{"source": "backup.zip", "destination": "D:\\"}}}}
User: "Launch Notepad" -> {{"tool": "launch_application", "params": {{"app_name": "notepad"}}}}
User: "Open Chrome" -> {{"tool": "launch_application", "params": {{"app_name": "chrome"}}}}
"""


class OrchestratorMCP:
    def __init__(self, model_name: str = "llama3.2:1b"):
        self.model = model_name

    def handle(self, user_text: str):
        messages = [
            {"role": "system", "content": PERSONA},
            {"role": "user", "content": user_text},
        ]

        system_intent = self._looks_like_system_intent(user_text)

        # Fast-path for known tool intents that should not rely on JSON formatting
        low = user_text.lower()
        if system_intent:
            if "window" in low:
                return {"tool": "get_active_window", "params": {}}
            if "clipboard" in low:
                return {"tool": "read_clipboard", "params": {}}
            if "open" in low or "launch" in low or "start" in low:
                # If user mentions an app without a path, pass app_name for resolver
                return {"tool": "launch_application", "params": {"app_name": user_text}}

        if not system_intent:
            # Bypass tool path for greetings/general chat
            plain = self._call_ollama(messages, expect_json=False)
            return plain if isinstance(plain, str) else "Unable to process request."

        # System intent: expect a tool call
        parsed = self._call_ollama(messages, expect_json=True)
        if isinstance(parsed, str):
            # JSON failed; ask for clarification to avoid guessing
            return "I need to know what to do: which drive or path should I use?"

        if not isinstance(parsed, dict):
            return "Please try again with a clear request."

        if "tool" in parsed:
            tool = parsed.get("tool")
            params = parsed.get("params", {}) if isinstance(parsed.get("params", {}), dict) else {}
            params = self._normalize_tool_params(user_text, tool, params)
            if tool not in output_schemas.TOOLS:
                return "Unsupported tool."
            return {"tool": tool, "params": params}

        if "answer" in parsed:
            # Model tried to answer without tool; push for explicit tool usage
            return "I should use a tool for that. Which drive or path should I inspect?"

        return "I could not determine your intent. Please rephrase."

    def _looks_like_system_intent(self, text: str) -> bool:
        t = text.lower()
        keywords = [
            "drive", "folder", "file", "directory", "list", "show", "open", "move", "copy", "create", "launch", "run", "path",
            "window", "clipboard", "app", "excel", "word", "chrome", "edge", "whatsapp", "teams", "notepad", "code", "sticky", "notes", "stickynotes"
        ]
        if any(k in t for k in keywords):
            return True
        import re as _re
        if _re.search(r"\b[a-z]:\\?", text, flags=_re.IGNORECASE):
            return True
        if _re.search(r"\b[a-z]\s+drive\b", text, flags=_re.IGNORECASE):
            return True
        return False

    def _extract_drive(self, text: str):
        import re as _re
        m = _re.search(r"\b([a-z]):\\?", text, flags=_re.IGNORECASE)
        if m:
            return m.group(1).upper() + ":"
        m2 = _re.search(r"\b([a-z])\s+drive\b", text, flags=_re.IGNORECASE)
        if m2:
            return m2.group(1).upper() + ":"
        return None

    def _normalize_tool_params(self, user_text: str, tool: str, params: dict) -> dict:
        import re as _re
        drive = self._extract_drive(user_text)

        def normalize_path(p: str) -> str:
            if not p:
                return p
            p = str(p).strip()
            # If drive is provided in text and path lacks drive, prepend it
            if drive and ":" not in p:
                if p.startswith("\\"):
                    p = p.lstrip("\\/")
                p = f"{drive}\\{p}"
            # Normalize bare drive letter to root
            if len(p) == 2 and p[1] == ":":
                p = p + "\\"
            if p == "/" or p == "\\":
                # If user mentioned a drive, use its root; else keep as root
                if drive:
                    p = f"{drive}\\"
                else:
                    p = "/"
            return p

        # For move/copy: extract explicit paths and folder references from user text
        if tool in {"move_file", "copy_file"}:
            # Look for explicit paths: D:\notes.txt, D:\archive, etc.
            paths_in_text = _re.findall(r'([a-z]:\\[^\s"]+)', user_text, flags=_re.IGNORECASE)
            
            # Extract filename if mentioned (e.g., "Zxdy.pdf", "notes.txt")
            filename_match = _re.search(r'\b([\w\-\.]+\.\w{2,4})\b', user_text)
            filename = filename_match.group(1) if filename_match else None
            
            # Extract folder names mentioned (e.g., "from SDM", "to projects")
            # Look for patterns like "from X" or "to Y" where X/Y are folder names
            from_folder = _re.search(r'\bfrom\s+([\w\-]+)', user_text, flags=_re.IGNORECASE)
            to_folder = _re.search(r'\bto\s+([\w\-]+)(?:\s+folder)?', user_text, flags=_re.IGNORECASE)
            
            # Build source path
            if len(paths_in_text) >= 1:
                # Explicit path found
                if "source" in params:
                    llm_source = str(params.get("source", "")).strip()
                    if llm_source and ":" in llm_source and llm_source.count("\\") > 0:
                        params["source"] = normalize_path(llm_source)
                    else:
                        params["source"] = paths_in_text[0]
                else:
                    params["source"] = paths_in_text[0]
            elif from_folder and filename and drive:
                # Build source from folder + filename: F:\SDM\Zxdy.pdf
                folder_name = from_folder.group(1)
                params["source"] = f"{drive}\\{folder_name}\\{filename}"
            elif filename and drive:
                # Just filename with drive: F:\Zxdy.pdf
                params["source"] = f"{drive}\\{filename}"
            elif "source" in params:
                params["source"] = normalize_path(params.get("source"))
            
            # Build destination path
            if len(paths_in_text) >= 2:
                # Second explicit path
                if "destination" in params:
                    llm_dest = str(params.get("destination", "")).strip()
                    if llm_dest and ":" in llm_dest and llm_dest.count("\\") > 0:
                        params["destination"] = normalize_path(llm_dest)
                    else:
                        params["destination"] = paths_in_text[1]
                else:
                    params["destination"] = paths_in_text[1]
            elif to_folder and drive:
                # Build destination from folder name: F:\projects
                folder_name = to_folder.group(1)
                params["destination"] = f"{drive}\\{folder_name}"
            elif "destination" in params:
                params["destination"] = normalize_path(params.get("destination"))
            
            # Final normalization with backslash fixes
            if "source" in params:
                src = params["source"]
                # Fix missing backslash after drive: F:Zxdy.pdf -> F:\Zxdy.pdf
                if len(src) > 2 and src[1] == ":" and src[2] != "\\":
                    src = src[0:2] + "\\" + src[2:]
                # Convert forward slashes to backslashes
                src = src.replace("/", "\\")
                params["source"] = src
                
            if "destination" in params:
                dst = params["destination"]
                if len(dst) > 2 and dst[1] == ":" and dst[2] != "\\":
                    dst = dst[0:2] + "\\" + dst[2:]
                dst = dst.replace("/", "\\")
                params["destination"] = dst

        elif tool in {"list_directory", "read_file"}:
            if "path" in params:
                params["path"] = normalize_path(params.get("path"))

        elif tool == "create_directory":
            if "path" in params:
                params["path"] = normalize_path(params.get("path"))

        elif tool == "launch_application":
            if "exe_path" in params:
                params["exe_path"] = normalize_path(params.get("exe_path"))
            if "app_name" not in params or not params.get("app_name"):
                # Use raw user text as fallback app name when path is not provided
                params["app_name"] = user_text

        if tool == "find_file":
            if drive:
                params["search_roots"] = [f"{drive}\\"]

        return params

    def _call_ollama(self, messages, expect_json: bool):
        """Call Ollama with a timeout and return parsed JSON or raw text; on error, return error string."""
        try:
            start = time.time()
            if expect_json:
                resp = ollama.chat(model=self.model, messages=messages, format="json")
                content = resp.get("message", {}).get("content", "").strip()
                return json.loads(content)
            else:
                resp = ollama.chat(model=self.model, messages=messages)
                return resp.get("message", {}).get("content", "").strip()
        except Exception as e:
            return f"LLM error: {e}"
