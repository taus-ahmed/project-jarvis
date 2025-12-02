import customtkinter as ctk
import threading
import json
import google.generativeai as genai
import speech_recognition as sr
from PIL import ImageGrab
import time
import os
import re
import datetime

# Import Modules
from config import GENAI_KEY
from utils import speak
import skills
import system_ops 

class JarvisApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("JARVIS - ULTIMATE MODE")
        self.geometry("500x750")
        ctk.set_appearance_mode("dark")
        
        self.chat_session = None 
        self.is_listening = False
        self.stop_signal = False
        self.recognizer = sr.Recognizer()
        
        # --- UI ELEMENTS ---
        self.status_label = ctk.CTkLabel(self, text="INITIALIZING...", font=("Arial", 16, "bold"))
        self.status_label.pack(pady=10)
        
        self.log_box = ctk.CTkTextbox(self, width=450, height=550, text_color="#00ff00", font=("Consolas", 12))
        self.log_box.pack(pady=10)
        
        self.listen_btn = ctk.CTkButton(self, text="START LISTENING", command=self.toggle_listening, fg_color="green")
        self.listen_btn.pack(pady=10)

        # --- AI SETUP ---
        try:
            genai.configure(api_key=GENAI_KEY)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
            
            # --- INTELLIGENT SYSTEM PROMPT ---
            system_instruction = """
            You are Jarvis, an advanced Windows Automation Agent.
            
            RULES:
            1. Return strictly VALID JSON.
            2. For 'open' actions, use the exact Windows command (e.g., 'winword', 'chrome', 'calc', 'whatsapp:').
            3. VISION: If the user sends an image (screen analysis), analyze it and return action="chat" with the description in 'message'.
            4. VOLUME: If user says "set volume to X" or "volume 50", return action="media" with target="to X".
            
            Valid Actions & Targets:
            - "open": target="app_name" or "file_path"
            - "google": target="search_query" (e.g., "what is rag ai")
            - "search": target="filename" (e.g., "config in backend")
            - "create_folder": target="folder_name"
            - "wifi": target="on" or "off"
            - "bluetooth": target="on" or "off"
            - "media": target="volume_up", "volume_down", "mute", "play", "pause", "next", "previous", "to 50"
            - "recycle": target="exact_file_path" (Only used AFTER confirmation)
            - "system": target="battery", "cpu", "ram", "all"
            - "clipboard": target="read"
            - "time": target="current"
            - "chat": target=""
            
            Response JSON Structure:
            {"action": "action_name", "target": "target_value", "message": "Spoken response"}
            """
            
            self.chat_session = self.model.start_chat(history=[
                {"role": "user", "parts": "System initialized."},
                {"role": "model", "parts": "Acknowledged."}
            ])
            self.chat_session.send_message(system_instruction)
            
            self.status_label.configure(text="SYSTEM ONLINE")
            self.log("System: AI Connected Successfully.")
            
        except Exception as e:
            self.status_label.configure(text="AI ERROR")
            self.log(f"CRITICAL ERROR: {e}")

    def log(self, message):
        self.log_box.insert("end", f"{message}\n")
        self.log_box.see("end")

    def toggle_listening(self):
        if not self.is_listening:
            self.is_listening = True
            self.stop_signal = False
            self.listen_btn.configure(text="STOP (INTERRUPT)", fg_color="red")
            self.status_label.configure(text="LISTENING...")
            threading.Thread(target=self.background_listener, daemon=True).start()
        else:
            self.is_listening = False
            self.stop_signal = True 
            self.listen_btn.configure(text="START LISTENING", fg_color="green")
            self.status_label.configure(text="STANDBY")

    def speak_clean(self, text):
        if self.stop_signal: return
        clean_text = re.sub(r'[A-Z]:\\[\w\\\.\-_ ]+\\([\w\.\-_ ]+)', r'\1', text)
        speak(clean_text)

    def background_listener(self):
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            while self.is_listening:
                if self.stop_signal: break
                try:
                    audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)
                    try:
                        text = self.recognizer.recognize_google(audio).lower()
                        self.log(f"[HEARD]: '{text}'") 
                        self.process_command(text)
                    except sr.UnknownValueError: pass 
                except: pass

    def extract_json(self, text):
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try: return json.loads(match.group(0))
            except: pass
        return None

    def process_command(self, command):
        if self.stop_signal: return
        self.log(f"[PROCESSING]: {command}")
        
        try:
            # --- VISION HANDLER ---
            vision_keywords = ["look", "see", "screen", "read this", "analyze"]
            # Avoid triggering vision for "search for file" commands
            if any(k in command.lower() for k in vision_keywords) and "search" not in command:
                self.log("[VISION]: Capturing screen...")
                screenshot = ImageGrab.grab()
                response = self.chat_session.send_message([command, screenshot])
            else:
                response = self.chat_session.send_message(command)
            
            data = self.extract_json(response.text)
            
            if not data:
                data = {"action": "chat", "message": response.text, "target": ""}

            action = data.get("action")
            target = data.get("target") or ""
            message = data.get("message", "")

            if message:
                self.log(f"Jarvis: {message}")
                self.speak_clean(message)

            # --- ACTION HANDLERS ---
            if action == "search":
                self.log(f"[SYS] Searching for: {target}")
                result = skills.deep_search(target)
                if result:
                    feedback = f"SYSTEM_RESULT: Found file at: '{result}'. Ask user if they want to OPEN it or DELETE it."
                    resp2 = self.chat_session.send_message(feedback)
                    data2 = self.extract_json(resp2.text)
                    if data2 and data2.get("message"):
                        self.log(f"Jarvis: {data2['message']}")
                        self.speak_clean(data2['message'])
                else:
                    self.speak_clean("I could not find that file.")

            elif action == "open":
                if ":" in target or "/" in target or "\\" in target:
                    self.log(f"Opening File: {target}")
                    os.startfile(target)
                else:
                    skills.open_app(target)

            elif action == "google":
                skills.search_google(target)

            elif action == "media":
                skills.control_media(target)
                
            elif action == "recycle":
                res = skills.recycle_file(target)
                self.log(res)

            elif action == "system":
                res = system_ops.get_system_status(target)
                self.log(res)

            elif action == "clipboard":
                res = system_ops.read_clipboard()
                self.log(f"Clipboard: {res}")
                
            elif action == "time":
                now = datetime.datetime.now().strftime("%I:%M %p on %A, %B %d")
                speak(f"It is {now}")
                self.log(now)

            elif action == "create_folder":
                res = skills.create_folder(target, "desktop")
                self.log(res)
            elif action == "wifi":
                skills.toggle_wifi(target)
            elif action == "bluetooth":
                skills.toggle_bluetooth(target)

        except Exception as e:
            self.log(f"[ERROR]: {e}")

if __name__ == "__main__":
    app = JarvisApp()
    app.mainloop()