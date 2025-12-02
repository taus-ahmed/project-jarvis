import os
import subprocess
import pyautogui
from send2trash import send2trash
from config import SEARCH_PATHS, IGNORE_FOLDERS, CHROME_PROFILE
from utils import speak, normalize

# --- CONSTANTS ---
BANNED_EXTENSIONS = {'.dll', '.sys', '.tmp', '.ini', '.log', '.dat', '.cab', '.exe.config'}

def open_app(target):
    speak(f"Opening {target}")
    if target == "chrome_profile":
        try:
            cmd = f'start chrome --profile-directory="{CHROME_PROFILE}"' 
            subprocess.Popen(cmd, shell=True)
        except:
            speak("Error opening Chrome profile.")
    elif target == "code":
        try:
            subprocess.Popen("code", shell=True)
        except:
            speak("Could not open VS Code.")
    else:
        try:
            subprocess.Popen(f"start {target}", shell=True)
        except:
            speak(f"Could not open {target}")

def open_vs_code_folder(path):
    speak(f"Opening VS Code in {os.path.basename(path)}")
    try:
        subprocess.Popen(f'code "{path}"', shell=True)
        return f"Opened VS Code in {path}"
    except Exception as e:
        return f"Error opening VS Code: {e}"

def find_folder_path(target_folder_name):
    """
    Scans drives to find the full path of a requested folder.
    Uses fuzzy matching so 'dump code' finds 'dump_code'.
    """
    target_clean = normalize(target_folder_name) 
    
    speak(f"Locating folder {target_folder_name}...")
    
    for path in SEARCH_PATHS:
        if not os.path.exists(path): continue
        try:
            for root, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs if d not in IGNORE_FOLDERS]
                for dirname in dirs:
                    if target_clean in normalize(dirname):
                        return os.path.join(root, dirname)
        except: continue
    return None

def create_code_file(filename, content, target_folder=None):
    try:
        save_path = ""
        if target_folder:
            found_path = find_folder_path(target_folder)
            if found_path:
                save_path = found_path
                speak(f"Found folder {os.path.basename(save_path)}.")
            else:
                speak(f"Could not find folder {target_folder}. Defaulting to Desktop.")
        
        if not save_path:
            user_home = os.path.expanduser("~")
            desktop = os.path.join(user_home, "Desktop")
            onedrive_desktop = os.path.join(user_home, "OneDrive", "Desktop")
            if os.path.exists(desktop): save_path = desktop
            elif os.path.exists(onedrive_desktop): save_path = onedrive_desktop
            else: save_path = user_home 
            
        file_path = os.path.join(save_path, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        speak(f"Creating {filename}...")
        subprocess.Popen(f'code "{file_path}"', shell=True)
        return f"Created {filename} in {os.path.basename(save_path)}"
    except Exception as e:
        return f"Error creating file: {e}"

def control_media(target):
    if target == "volume_up": 
        for _ in range(5): pyautogui.press("volumeup")
    elif target == "volume_down": 
        for _ in range(5): pyautogui.press("volumedown")
    elif target == "mute": 
        pyautogui.press("volumemute")
    elif target == "play_pause":
        pyautogui.press("playpause")
    elif "volume_set" in target:
        try:
            level = int(target.split("_")[-1])
            for _ in range(50): pyautogui.press("volumedown")
            for _ in range(int(level/2)): pyautogui.press("volumeup")
            speak(f"Volume set to {level}")
            return
        except: pass
    speak(f"Media control: {target}")

def get_folder_score(path, target_name):
    score = 0
    try:
        name = os.path.basename(path).lower()
        target = target_name.lower()
        
        # Scoring Rules
        if name == target: score += 1000
        elif name.startswith(target): score += 100
        elif target in name: score += 50
        
        # Penalize system paths
        if any(x in path for x in ["AppData", "Program Files", "node_modules", "site-packages", "lib", "Windows", "Config"]):
            score -= 500
            
    except: pass
    return score

def search_file(target, open_in_vscode=False):
    clean_target = target.lower().replace(" folder", "").replace(" file", "").strip()
    speak(f"Searching for {clean_target}...")
    target_clean = normalize(clean_target)
    candidates = []

    for path in SEARCH_PATHS:
        if not os.path.exists(path): continue
        try:
            for root, dirs, files in os.walk(path):
                # Filter junk
                dirs[:] = [d for d in dirs if d not in IGNORE_FOLDERS]
                
                # Check Folders
                for dirname in dirs:
                    if target_clean in normalize(dirname):
                        full_path = os.path.join(root, dirname)
                        score = get_folder_score(full_path, clean_target)
                        candidates.append((score, full_path, "folder"))

                # Check Files
                if not open_in_vscode:
                    for filename in files:
                        # Ignore banned extensions
                        if any(filename.lower().endswith(ext) for ext in BANNED_EXTENSIONS):
                            continue
                            
                        if target_clean in normalize(filename):
                            full_path = os.path.join(root, filename)
                            score = 100 if normalize(filename) == target_clean else 50
                            if "AppData" in full_path or "Program Files" in full_path: score -= 500
                            candidates.append((score, full_path, "file"))
        except: continue

    if not candidates:
        speak("I could not find that.")
        return "Not found."

    candidates.sort(key=lambda x: x[0], reverse=True)
    best_match = candidates[0][1]
    
    if open_in_vscode:
        return open_vs_code_folder(best_match)
    
    if candidates[0][2] == "folder":
        os.startfile(best_match)
        return f"Opened Folder: {os.path.basename(best_match)}"
    else:
        subprocess.Popen(f'explorer /select,"{best_match}"')
        return f"Opened File: {os.path.basename(best_match)}"

def delete_file(target):
    speak(f"Deleting {target}")
    target_clean = normalize(target)
    for path in SEARCH_PATHS:
        if not os.path.exists(path): continue
        try:
            for root, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs if d not in IGNORE_FOLDERS]
                for filename in files:
                    if target_clean in normalize(filename):
                        full_path = os.path.join(root, filename)
                        try:
                            send2trash(full_path)
                            speak("File recycled.")
                            return "File Recycled"
                        except:
                            speak("Error deleting.")
                            return
        except: continue
    speak("File not found.")
    return "Delete failed"