import sys
import json
import struct
import subprocess
import os
import google.generativeai as genai
import pyautogui
from send2trash import send2trash
import pyttsx3

# --- CONFIGURATION ---
GENAI_KEY = "AIzaSyDoH8xVNYHHV3_sAfxm-qtdQLqy7FHGEpU"
SEARCH_ROOT = "F:\\"

# --- REDIRECT PRINT TO STDERR (CRITICAL FOR CHROME) ---
# Any normal print() will now go to the error log, not breaking Chrome
def log(message):
    sys.stderr.write(f"{message}\n")
    sys.stderr.flush()

try:
    genai.configure(api_key=GENAI_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    log(f"Gemini Error: {e}")

# --- VOICE ENGINE (Initialize ONCE) ---
try:
    engine = pyttsx3.init()
    engine.setProperty('rate', 180)
except Exception as e:
    log(f"Voice Init Error: {e}")
    engine = None

def speak(text):
    """Makes Jarvis talk safely"""
    if not engine:
        return
    try:
        log(f"Jarvis Speaking: {text}")
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        log(f"Voice Error: {e}")

def get_message():
    try:
        raw_length = sys.stdin.buffer.read(4)
        if len(raw_length) == 0:
            return None
        message_length = struct.unpack('@I', raw_length)[0]
        message = sys.stdin.buffer.read(message_length).decode('utf-8')
        return json.loads(message)
    except Exception as e:
        log(f"Read Error: {e}")
        return None

def send_message(message_content):
    try:
        encoded_content = json.dumps(message_content).encode('utf-8')
        encoded_length = struct.pack('@I', len(encoded_content))
        sys.stdout.buffer.write(encoded_length)
        sys.stdout.buffer.write(encoded_content)
        sys.stdout.buffer.flush()
    except Exception as e:
        log(f"Send Error: {e}")

def ask_gemini(command):
    prompt = f"""
    You are Jarvis, a Windows Automation Assistant.
    The user will give a voice command. Interpret it and return a JSON object.
    
    Supported Actions:
    1. "open": Open an app (e.g., "notepad.exe", "calc.exe", "code").
    2. "search": Search for a file/folder. Target is the name.
    3. "media": Control playback. Target: "volume_up", "volume_down", "mute", "play_pause".
    4. "delete": Recycle a file. Target is the filename.
    5. "chat": General question/conversation. Target is your spoken reply (keep it brief, 1-2 sentences).
    
    USER COMMAND: "{command}"
    
    RETURN ONLY JSON. Examples: 
    {{"action": "chat", "target": "Sir, the capital of France is Paris."}}
    {{"action": "open", "target": "notepad.exe"}}
    """
    try:
        response = model.generate_content(prompt)
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except Exception as e:
        log(f"AI Error: {e}")
        return {"action": "chat", "target": "I'm having trouble connecting to the brain."}

def normalize(text):
    return "".join(char for char in text if char.isalnum()).lower()

def execute_action(ai_decision):
    action = ai_decision.get("action")
    target = ai_decision.get("target")
    
    if action == "chat":
        speak(target)
        return target

    elif action == "open":
        speak(f"Opening {target}")
        try:
            subprocess.Popen(target, shell=True)
            return f"Opening {target}"
        except:
            speak("I couldn't open that.")
            return f"Could not open {target}"

    elif action == "media":
        if target == "volume_up": pyautogui.press("volumeup")
        elif target == "volume_down": pyautogui.press("volumedown")
        elif target == "mute": pyautogui.press("volumemute")
        elif target == "play_pause": pyautogui.press("playpause")
        return f"Media control: {target}"

    elif action == "search":
        speak(f"Searching for {target}")
        target_clean = normalize(target)
        for root, dirs, files in os.walk(SEARCH_ROOT):
            for dirname in dirs:
                if target_clean in normalize(dirname):
                    full_path = os.path.join(root, dirname)
                    subprocess.Popen(f'explorer "{full_path}"')
                    return f"Found Folder: {dirname}"
            for filename in files:
                if target_clean in normalize(filename):
                    full_path = os.path.join(root, filename)
                    subprocess.Popen(f'explorer /select,"{full_path}"')
                    return f"Found File: {filename}"
        speak("I couldn't find anything.")
        return f"Not found: {target}"

    elif action == "delete":
        speak(f"Deleting {target}")
        target_clean = normalize(target)
        file_to_delete = None
        for root, dirs, files in os.walk(SEARCH_ROOT):
            for filename in files:
                if target_clean in normalize(filename):
                    file_to_delete = os.path.join(root, filename)
                    break
            if file_to_delete: break
        
        if file_to_delete:
            try:
                send2trash(file_to_delete)
                return f"Recycled: {os.path.basename(file_to_delete)}"
            except Exception as e:
                return f"Error deleting: {e}"
        else:
            speak("File not found.")
            return "File not found."

    return "I'm not sure how to do that."

# Main Loop
while True:
    msg = get_message()
    if msg:
        ai_decision = ask_gemini(msg.get("text", ""))
        result_text = execute_action(ai_decision)
        send_message({"message": result_text})
    else:
        break