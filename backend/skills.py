import os
import subprocess
import json
import ctypes
import time
import re
import pyautogui
from send2trash import send2trash 
from config import IGNORE_FOLDERS, MEMORY_FILE, CHROME_PROFILE
from utils import speak, normalize

# --- MEMORY SYSTEM ---
def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r") as f:
                return json.load(f)
        except: return {}
    return {}

def save_memory(key, path):
    data = load_memory()
    data[key] = path
    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f, indent=4)

# --- SYSTEM DISCOVERY ---
def get_available_drives():
    drives = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for letter in range(65, 91): # A-Z
        if bitmask & 1:
            drives.append(f"{chr(letter)}:\\")
        bitmask >>= 1
    return drives

def deep_search(target_name):
    if not target_name: return None
    folder_hint = None
    if " in " in target_name:
        parts = target_name.split(" in ")
        target_name = parts[0].strip()
        folder_hint = parts[1].strip().lower()
    clean_target = normalize(target_name)
    target_lower = target_name.lower()
    if not folder_hint:
        mem = load_memory()
        if clean_target in mem:
            if os.path.exists(mem[clean_target]):
                return mem[clean_target]
            else:
                del mem[clean_target] 
    drives = get_available_drives()
    partial_matches = []
    for drive in drives:
        for root, dirs, files in os.walk(drive):
            dirs[:] = [d for d in dirs if d not in IGNORE_FOLDERS]
            if folder_hint and folder_hint not in root.lower(): continue
            for f in files:
                if f.lower() == target_lower:
                    full_path = os.path.join(root, f)
                    save_memory(clean_target, full_path)
                    return full_path
                if clean_target in normalize(f) and not f.endswith(('.pyc', '.pyd', '.dll')):
                    partial_matches.append(os.path.join(root, f))
            for d in dirs:
                if d.lower() == target_lower:
                    full_path = os.path.join(root, d)
                    save_memory(clean_target, full_path)
                    return full_path
    if partial_matches:
        partial_matches.sort(key=len)
        return partial_matches[0]
    return None

# --- MEDIA CONTROL (RELIABLE LOOP) ---
def control_media(action):
    action = action.lower()
    
    # 1. Handle Tracks
    if "next" in action or "skip" in action:
        pyautogui.press("nexttrack")
        return
    elif "previous" in action or "back" in action:
        pyautogui.press("prevtrack")
        return

    # 2. Volume Logic
    nums = re.findall(r'\d+', action)
    val = int(nums[-1]) if nums else None
    
    # "Set to X" Logic - The Reset Method
    if "to" in action and val is not None:
        speak(f"Setting volume to {val} percent.")
        
        # Step 1: Mute/Reset to 0 by pressing down 50 times
        for _ in range(50):
            pyautogui.press("volumedown")
            time.sleep(0.01) # Tiny pause to ensure registry
            
        # Step 2: Increase to target (Val / 2 because each press is 2%)
        steps = int(val / 2)
        for _ in range(steps):
            pyautogui.press("volumeup")
            time.sleep(0.01)
        return

    # Standard Increase/Decrease
    if "volume up" in action or "increase" in action:
        steps = int(val/2) if val else 5
        for _ in range(steps):
            pyautogui.press("volumeup")
            time.sleep(0.01)
        speak("Volume increased.")
            
    elif "volume down" in action or "decrease" in action:
        steps = int(val/2) if val else 5
        for _ in range(steps):
            pyautogui.press("volumedown")
            time.sleep(0.01)
        speak("Volume decreased.")
            
    elif "mute" in action or "silent" in action:
        pyautogui.press("volumemute")
        speak("Muted.")
    elif "play" in action or "pause" in action:
        pyautogui.press("playpause")

# --- APP & WEB CONTROL ---
def open_app(target):
    if not target: return
    
    # 1. Special Apps
    if "whatsapp" in target.lower():
        speak("Opening WhatsApp...")
        try:
            subprocess.Popen("start whatsapp:", shell=True)
            return
        except: pass
        
    # 2. Generic Open
    speak(f"Opening {target}")
    try:
        subprocess.Popen(f"start {target}", shell=True)
    except:
        speak(f"Could not open {target}")

def search_google(query):
    """Opens a Google Search for the given query."""
    speak(f"Searching Google for {query}...")
    formatted_query = query.replace(" ", "+")
    try:
        subprocess.Popen(f"start https://www.google.com/search?q={formatted_query}", shell=True)
    except Exception as e:
        speak("Error opening browser.")

# --- NETWORK ---
def toggle_wifi(state):
    if state == "off":
        speak("Disconnecting Wi-Fi...")
        subprocess.run('netsh wlan disconnect', shell=True)
    else:
        speak("Connecting to Wi-Fi...")
        try:
            result = subprocess.check_output('netsh wlan show profiles', shell=True).decode('utf-8', errors='ignore')
            profiles = re.findall(r"All User Profile\s*:\s*(.*)", result)
            if profiles:
                subprocess.run(f'netsh wlan connect name="{profiles[0].strip()}"', shell=True)
            else:
                speak("No saved networks found.")
        except: speak("Error connecting.")

def toggle_bluetooth(state):
    speak(f"Opening Bluetooth settings.")
    subprocess.Popen("start ms-settings:bluetooth", shell=True)

# --- FILES ---
def recycle_file(target_path):
    if not target_path or not os.path.exists(target_path):
        return "File not found."
    try:
        filename = os.path.basename(target_path)
        speak(f"Recycling {filename}...")
        send2trash(target_path)
        return "File recycled."
    except: return "Error recycling file."

def create_folder(folder_name, location_query):
    base_path = os.path.join(os.path.expanduser("~"), "Desktop")
    if location_query and "documents" in location_query.lower():
        base_path = os.path.join(os.path.expanduser("~"), "Documents")
    final_path = os.path.join(base_path, folder_name)
    try:
        os.makedirs(final_path, exist_ok=True)
        save_memory(normalize(folder_name), final_path)
        subprocess.Popen(f'explorer "{final_path}"')
        return f"Created {folder_name}"
    except: return "Error creating folder."