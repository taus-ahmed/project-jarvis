import os

# --- API KEYS ---
GENAI_KEY = "XYZ" 

# --- DYNAMIC PATHS (No more hardcoding) ---
# We use environment variables to find the user's specific paths
USER_HOME = os.path.expanduser("~")
DOWNLOADS = os.path.join(USER_HOME, "Downloads")
DOCUMENTS = os.path.join(USER_HOME, "Documents")
DESKTOP = os.path.join(USER_HOME, "Desktop")

# --- MEMORY FILE ---
# This file will store paths Jarvis has learned so he doesn't have to search twice.
MEMORY_FILE = "jarvis_memory.json"

# --- BROWSER SETTINGS ---
# We can add more profiles here if needed
CHROME_PROFILE = "Default" 

# --- IGNORED FOLDERS ---
# Folders Jarvis should skip to save time
IGNORE_FOLDERS = {
    'Windows', 'Program Files', 'Program Files (x86)', 'AppData', 
    '$Recycle.Bin', 'anaconda3', 'node_modules', '.git', 
    '__pycache__', 'site-packages', 'lib', 'venv'
}
