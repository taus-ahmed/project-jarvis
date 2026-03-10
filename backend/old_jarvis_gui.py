import customtkinter as ctk
import threading
import sys
import os
import json
import google.generativeai as genai
import pyttsx3
import pyautogui
from send2trash import send2trash
import speech_recognition as sr
import subprocess
from PIL import Image, ImageGrab
import io
import re
import string 

# --- CONFIGURATION ---
GENAI_KEY = "XYZ"  # <--- PASTE YOUR API KEY HERE
CHROME_PROFILE = "Default"

# --- SMART DRIVE DETECTION ---
def get_search_paths():
    """
    Returns prioritized paths.
    1. User User Profile (Desktop, Documents, Downloads)
    2. External Drives (D:, F:, etc.)
    3. C: Root (last priority)
    """
    paths = []
    
    # 1. User Home (Desktop, Downloads, etc.)
    user_path = os.path.expanduser("~")
    paths.append(user_path)
    
    # 2. All Drives
    for d in string.ascii_uppercase:
        drive_path = f'{d}:\\'
        if os.path.exists(drive_path):
            # We add all drives, but the search logic will prioritize exact matches
            if drive_path not in paths:
                paths.append(drive_path)
            
    return paths

# --- SETUP AI ---
try:
    genai.configure(api_key=GENAI_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    print(f"AI Init Error: {e}")

# --- HELPER FUNCTIONS ---

def clean_text_for_speech(text):
    text = re.sub(r'\*+', '', text)
    text = text.replace('`', '')
    text = text.replace('#', '')
    text = " ".join(text.split())
    return text

def speak(text):
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 180)
        clean_text = clean_text_for_speech(text)
        engine.say(clean_text)
        engine.runAndWait()
    except Exception as e:
        print(f"Voice Error: {e}")

def normalize(text):
    """
    Aggressive normalization.
    'SDM Folder' -> 'sdmfolder'
    'host.py' -> 'hostpy'
    """
    return "".join(char for char in text if char.isalnum()).lower()

# --- MAIN GUI APPLICATION CLASS ---

class JarvisApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("JARVIS")
        self.geometry("400x650")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")

        self.label = ctk.CTkLabel(self, text="PROJECT JARVIS", font=("Courier New", 24, "bold"), text_color="#00ff41")
        self.label.pack(pady=20)

        self.status_label = ctk.CTkLabel(self, text="SYSTEM ONLINE", font=("Arial", 16))
        self.status_label.pack(pady=10)

        self.log_box = ctk.CTkTextbox(self, width=350, height=350, text_color="#00ff41")
        self.log_box.pack(pady=10)
        self.log("Initializing system...")

        self.listen_btn = ctk.CTkButton(self, text="LISTEN", command=self.start_listening_thread, width=200, height=50, fg_color="#004411", hover_color="#00ff41")
        self.listen_btn.pack(pady=20)

        self.recognizer = sr.Recognizer()

    def log(self, message):
        self.log_box.insert("end", f"> {message}\n")
        self.log_box.see("end")

    def start_listening_thread(self):
        self.listen_btn.configure(state="disabled", text="LISTENING...")
        threading.Thread(target=self.listen_mic).start()

    def listen_mic(self):
        with sr.Microphone() as source:
            self.status_label.configure(text="LISTENING...", text_color="#00ff41")
            self.log("Listening...")
            try:
                audio = self.recognizer.listen(source, timeout=5)
                self.status_label.configure(text="PROCESSING...", text_color="#ffff00")
                command = self.recognizer.recognize_google(audio)
                self.log(f"Heard: {command}")
                self.process_command(command)
            except sr.WaitTimeoutError:
                self.log("No speech detected.")
                self.status_label.configure(text="TIMEOUT", text_color="#ff0000")
            except sr.UnknownValueError:
                self.log("Could not understand audio.")
                self.status_label.configure(text="UNKNOWN", text_color="#ff0000")
            except Exception as e:
                self.log(f"Error: {e}")
                self.status_label.configure(text="ERROR", text_color="#ff0000")
            
            self.listen_btn.configure(state="normal", text="LISTEN")
            self.after(2000, lambda: self.status_label.configure(text="SYSTEM ONLINE", text_color="#ffffff"))

    def process_command(self, command):
        threading.Thread(target=self.run_ai, args=(command,)).start()

    def run_ai(self, command):
        if any(phrase in command.lower() for phrase in ["look at", "what is on", "read this", "tell me what", "see"]):
            self.handle_vision(command)
            return

        # UPDATED PROMPT: More flexible "search" logic
        prompt = f"""
        You are Jarvis, a Windows Automation Assistant.
        User says: "{command}".
        Interpret the intent and return a JSON object.
        
        Supported Actions:
        1. "open": Open a standard app (e.g. Notepad, Chrome, Spotify).
           - IF the user asks to open a specific FOLDER or FILE (like "Open SDM", "Open Images"), use "search".
           - "Word" -> "winword"
           - "PowerPoint" -> "powerpnt"
           - "Excel" -> "excel"
           - "Chrome" -> "chrome_profile"
        2. "search": Search for a file/folder and open it.
        3. "media": Control playback (volume_up, volume_down, mute, play_pause, volume_set_X).
        4. "delete": Recycle a file.
        5. "chat": General conversation.
        
        IF user asks general knowledge, use "chat".
        RETURN ONLY JSON. Example: {{"action": "search", "target": "images"}}
        """
        try:
            response = model.generate_content(prompt)
            text = response.text.replace("```json", "").replace("```", "").strip()
            
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                data = {"action": "chat", "target": text}

            action = data.get("action")
            target = data.get("target")
            
            if action == "chat":
                self.after(0, self.log, f"Jarvis: {target}")
                speak(target)
            elif action == "open":
                self.after(0, self.log, f"Jarvis: Opening {target}")
                speak(f"Opening {target}")
                if target == "chrome_profile":
                    try:
                        cmd = f'start chrome --profile-directory="{CHROME_PROFILE}"'
                        subprocess.Popen(cmd, shell=True)
                    except:
                        speak("Error opening Chrome profile.")
                else:
                    try: subprocess.Popen(f"start {target}", shell=True)
                    except: speak("Error opening app.")
            elif action == "media": self.handle_media(target)
            elif action == "search": self.handle_search(target)
            elif action == "delete": self.handle_delete(target)
            else: 
                self.after(0, self.log, f"Jarvis: {target}")
                speak(target)

        except Exception as e:
            self.after(0, self.log, f"AI Error: {e}")
            speak("I encountered an error.")

    def handle_vision(self, user_question):
        self.after(0, self.log, "Jarvis: Analyzing screen...")
        speak("Taking a look...")
        try:
            screenshot = ImageGrab.grab()
            prompt = ["Analyze this screen and answer the user's question.", user_question, screenshot]
            response = model.generate_content(prompt)
            answer = response.text
            self.after(0, self.log, f"Jarvis: {answer[:100]}...") 
            speak(answer) 
        except Exception as e:
            self.after(0, self.log, f"Vision Error: {e}")
            speak("I could not analyze the screen.")

    def handle_media(self, target):
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
            except:
                pass
        self.after(0, self.log, f"Jarvis: Media ({target})")
        speak(f"Media control: {target}")

    def handle_search(self, target):
        self.after(0, self.log, f"Jarvis: Searching {target}...")
        speak(f"Searching for {target}")
        
        target_clean = normalize(target)
        search_paths = get_search_paths() 
        
        # IGNORE LIST (Skip massive system folders to speed up search)
        IGNORE_FOLDERS = {'Windows', 'Program Files', 'Program Files (x86)', 'AppData', '$Recycle.Bin'}

        # --- PASS 1: EXACT MATCHES (Priority) ---
        # Scan ALL drives for an EXACT match first.
        # This prevents "MSDM" (partial) from beating "SDM" (exact).
        self.after(0, self.log, "Jarvis: Scanning for exact match...")
        
        for search_path in search_paths:
            try:
                for root, dirs, files in os.walk(search_path):
                    # Filter out system folders
                    dirs[:] = [d for d in dirs if d not in IGNORE_FOLDERS]

                    # 1a. Check Folders (Exact)
                    for dirname in dirs:
                        if normalize(dirname) == target_clean:
                            full_path = os.path.join(root, dirname)
                            os.startfile(full_path)
                            self.after(0, self.log, f"Jarvis: Found Folder {dirname}")
                            return
                    
                    # 1b. Check Files (Exact)
                    for filename in files:
                        if normalize(filename) == target_clean:
                            full_path = os.path.join(root, filename)
                            subprocess.Popen(f'explorer /select,"{full_path}"')
                            self.after(0, self.log, f"Jarvis: Found File {filename}")
                            return
            except: continue

        # --- PASS 2: FUZZY MATCHES (Fallback) ---
        # If we reach here, no exact match was found on ANY drive.
        self.after(0, self.log, "Jarvis: No exact match, trying fuzzy...")
        
        for search_path in search_paths:
            try:
                for root, dirs, files in os.walk(search_path):
                    dirs[:] = [d for d in dirs if d not in IGNORE_FOLDERS]

                    for dirname in dirs:
                        if target_clean in normalize(dirname):
                            full_path = os.path.join(root, dirname)
                            os.startfile(full_path)
                            self.after(0, self.log, f"Jarvis: Found fuzzy folder {dirname}")
                            return
                    for filename in files:
                        if target_clean in normalize(filename):
                            full_path = os.path.join(root, filename)
                            subprocess.Popen(f'explorer /select,"{full_path}"')
                            self.after(0, self.log, f"Jarvis: Found fuzzy file {filename}")
                            return
            except: continue
        
        self.after(0, self.log, "Jarvis: Not found.")
        speak("I could not find that file anywhere.")

    def handle_delete(self, target):
        speak(f"Deleting {target}")
        target_clean = normalize(target)
        search_paths = get_search_paths()
        
        for search_path in search_paths:
            try:
                for root, dirs, files in os.walk(search_path):
                    if 'AppData' in dirs: dirs.remove('AppData')
                    for filename in files:
                        if target_clean in normalize(filename):
                            full_path = os.path.join(root, filename)
                            try:
                                send2trash(full_path)
                                self.after(0, self.log, "Jarvis: File recycled.")
                                speak("File recycled.")
                                return
                            except:
                                speak("Error deleting.")
                                return
            except:
                continue
        speak("File not found.")

if __name__ == "__main__":
    app = JarvisApp()
    app.mainloop()
