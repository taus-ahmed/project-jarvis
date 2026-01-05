import json
import re
import ollama
from Jarvis.mcp_filesystem import filesystem

class JarvisRouter:
    """
    Orchestrator v17: Professional Windows-Aware MCP Agent.
    - Specialized for Windows file systems (using backslashes and drive letters).
    - Strict JSON-to-Human synthesis pass to prevent technical leaks.
    - Zero-guessing policy with human-like fallback for ambiguity.
    """

    def __init__(self, model_name="llama3.2:1b"):
        self.model = model_name
        self.persona = self._build_persona()

    def _build_persona(self) -> str:
        return """
        You are JARVIS, a professional AI that lives on this Windows computer.

        WHAT YOU KNOW:
        - You have strong general/world knowledge (history, science, culture, current facts).
        - You understand Windows paths and drives (C:\, D:\) and use backslashes.
        - You do NOT know this machine's files until you inspect them with MCP tools.

        MCP FILESYSTEM TOOLS (the only system powers you have):
        - list_directory(path): list folders/files at a path (start with "C:\\" or "/" to see roots).
        - read_file(path): read a text file at an absolute path.
        - find_file(filename): search all drives for a filename.

        DECISION POLICY:
        - If the user asks a general knowledge question or is greeting/being social, answer directly in natural language.
        - If the user asks about files, folders, drives, or needs file actions, return a single JSON tool call. Do not describe directory contents without running a tool.
        - If a drive is named (e.g., F:), use that drive. If no drive is given, first list the root ("/") to discover drives.
        - Absolutely no guessing. If unclear, ask a brief human-style clarification.

        OUTPUT RULES:
        - For tool use, output JSON exactly in one object.
        - For direct answers, output plain text (no JSON).
        - Keep responses concise, clear, and professional.

        INTERNAL ROUTING FORMAT (for tool requests):
        {"tool": "list_directory", "params": {"path": "C:\\"}}
        {"tool": "read_file", "params": {"path": "C:\\path\\file.txt"}}
        {"tool": "find_file", "params": {"filename": "config.py"}}

        EXAMPLES:
        User: "Capital of France?" -> {"answer": "Paris is the capital of France."}
        User: "Show me F drive" -> {"tool": "list_directory", "params": {"path": "F:\\"}}
        User: "Check the E drive" -> {"tool": "list_directory", "params": {"path": "E:\\"}}
        User: "Look for project_summary" -> {"tool": "find_file", "params": {"filename": "project_summary"}}
        User: "Open the notes file in Documents" -> ask which file if unclear, then use find_file/read_file.
        """

    def handle_input(self, user_text):
        """
        Processes user input. Ensures the model differentiates between 
        general conversation and hardware commands.
        """
        system_intent = self._is_system_intent(user_text)

        messages = [
            {"role": "system", "content": self.persona}, 
            {"role": "user", "content": user_text}
        ]

        try:
            # Force JSON mode to ensure the router can parse the 'intent'
            response = ollama.chat(
                model=self.model, 
                messages=messages,
                format="json"
            )
            content = response["message"]["content"].strip()
            res = json.loads(content)
            
            # Case 1: The model determines it can answer directly
            if "answer" in res and "tool" not in res:
                if system_intent:
                    return self._handle_system_without_tool(user_text)
                return res["answer"]
            
            # Case 2: The model determines a system action is needed
            if "tool" in res:
                return self._process_tool(res["tool"], res.get("params", {}), user_text)

        except Exception as e:
            # Fallback for when the model gets confused or JSON is malformed
            return "I'm having trouble understanding that. Is this a system task or a general question?"

        return "I'm ready to help—tell me if you need system actions or general answers."

    def _process_tool(self, name, params, original_query):
        """
        Handles the execution of MCP tools and ensures the final 
        output is human-friendly.
        """
        try:
            # Windows Path Sanitization
            if "path" in params:
                p = str(params["path"]).strip()
                # Keep "/" as root discovery; only normalize bare drive letters
                if len(p) == 1 or (len(p) == 2 and p[1] == ":"):
                    drive = p[0].upper()
                    params["path"] = f"{drive}:\\"

            # Execute the actual Python code from the filesystem MCP
            data = self._execute_mcp(name, params)
            
            # THE SYNTHESIS PASS: Force the LLM to convert JSON/Lists into English
            synthesis = ollama.chat(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": (
                            "You are Jarvis. Summarize tool results concisely. "
                            "Do NOT add descriptions, speculation, or commentary. "
                            "List exactly what the tool returned, then offer a brief next-step question (e.g., 'Open one of these?'). "
                            "NEVER show raw JSON or code unless the user asked."
                        )
                    },
                    {"role": "user", "content": f"User Request: {original_query}\nSystem Data: {data}"}
                ]
            )
            return synthesis["message"]["content"]
        except Exception as e:
            return f"I encountered a hardware error while accessing the system: {str(e)}"

    def _handle_system_without_tool(self, user_text):
        """Fallback: if the LLM tried to answer a system request without a tool, force a tool or ask clarifying question."""
        drive = self._extract_drive(user_text)
        if drive:
            path = f"{drive}\\"
            return self._process_tool("list_directory", {"path": path}, user_text)
        # If no drive detected, ask for clarification
        return "I need to check with the filesystem. Which drive or folder should I inspect?"

    def _is_system_intent(self, text: str) -> bool:
        """Lightweight heuristic to detect filesystem intent."""
        t = text.lower()
        keywords = ["drive", "folder", "file", "directory", "list", "show", "open"]
        if any(k in t for k in keywords):
            return True
        if re.search(r"\b[a-z]:\\?", text, flags=re.IGNORECASE):
            return True
        if re.search(r"\b[a-z]\s+drive\b", text, flags=re.IGNORECASE):
            return True
        return False

    def _extract_drive(self, text: str):
        """Extract a drive letter from text if present."""
        m = re.search(r"\b([a-z]):\\?", text, flags=re.IGNORECASE)
        if m:
            return m.group(1).upper() + ":"
        m2 = re.search(r"\b([a-z])\s+drive\b", text, flags=re.IGNORECASE)
        if m2:
            return m2.group(1).upper() + ":"
        return None

    def _execute_mcp(self, name, params):
        """Direct link to the hardware-level filesystem server."""
        if name == "list_directory":
            path = params.get("path", "C:\\")
            return str(filesystem.list_directory(path))
        if name == "read_file":
            # Note: We keep read_file as is. stream-based reading would be added 
            # to the filesystem.py module first if needed.
            return filesystem.read_file(params.get("path"))
        if name == "find_file":
            return str(filesystem.find_file(params.get("filename")))
        return "The requested integration is currently unavailable."