import streamlit as st
from router.orchestrator_mcp import OrchestratorMCP
from Jarvis.mcp_filesystem import filesystem

# --- PAGE SETUP ---
st.set_page_config(page_title="Jarvis AI", page_icon="🤖", layout="wide")

# --- INITIALIZATION ---
# Initialize the MCP-oriented orchestrator (routing only)
if "router" not in st.session_state:
    st.session_state.router = OrchestratorMCP(model_name="llama3.2:1b")

st.title("🤖 JARVIS")
st.caption("Stateless MCP Orchestrator v3.0 | Zero-Context Intelligence")

# --- SIDEBAR ---
with st.sidebar:
    st.header("🧠 System Status")
    st.success("Direct MCP Link Active")
    st.info("Operating in Stateless Mode: Every request is processed as a fresh query.")

# --- TOOL EXECUTION HELPER ---
def execute_tool(tool_call: dict):
    name = tool_call.get("tool")
    params = tool_call.get("params", {}) if isinstance(tool_call.get("params", {}), dict) else {}

    try:
        if name == "list_directory":
            path = params.get("path")
            if not path:
                return "Tool error: path is required for list_directory"
            p = str(path).strip()
            if len(p) == 2 and p[1] == ":":
                p = p + "\\"
            if p == "\\":
                p = "/"
            return filesystem.list_directory(p)
        if name == "read_file":
            return filesystem.read_file(params.get("path"))
        if name == "find_file":
            return filesystem.find_file(params.get("filename"), params.get("search_roots"))
        if name == "move_file":
            return filesystem.move_file(params.get("source"), params.get("destination"))
        if name == "copy_file":
            return filesystem.copy_file(params.get("source"), params.get("destination"))
        if name == "create_directory":
            return filesystem.create_directory(params.get("path"))
        if name == "launch_application":
            return filesystem.launch_application(
                params.get("exe_path"),
                params.get("args"),
                params.get("app_name")
            )
        if name == "write_file":
            return filesystem.write_file(params.get("path"), params.get("content", ""))
        if name == "get_active_window":
            return filesystem.get_active_window()
        if name == "read_clipboard":
            return filesystem.read_clipboard()
        return f"Unsupported tool: {name}"
    except Exception as e:
        return f"Tool error: {e}"


# --- CHAT UI ---
if prompt := st.chat_input("How can I help you today?"):
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Analyzing..."):
            try:
                routed = st.session_state.router.handle(prompt)
            except Exception as e:
                st.write(f"Router error: {e}")
                routed = None

            if isinstance(routed, dict) and "tool" in routed:
                st.info(f"Calling tool: {routed['tool']}")
                tool_result = execute_tool(routed)
                st.write(tool_result)
            elif routed is not None:
                st.write(routed)
            else:
                st.write("No response from router.")