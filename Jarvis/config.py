# config.py

ALLOWED_ROOT = r"C:\Jarvis Sandbox"
RESTRICTED_KEYWORDS = [
    "C:\\Windows", 
    "System32", 
    "AppData", 
    "System Volume Information",
    "Recovery",
    "$Recycle.Bin"
]

# Roots the orchestrator is allowed to search when using find_file.
# Forward slashes keep glob patterns consistent on Windows.
SEARCH_ROOTS = ["F:/", "D:/", "C:/", "./"]