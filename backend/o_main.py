import customtkinter as ctk
import threading
import json
import google.generativeai as genai
import speech_recognition as sr
from PIL import ImageGrab
import time
import re

# Import Modules
from config import GENAI_KEY
from utils import speak
import backend.old_skills as old_skills
import system_ops

class JarvisApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("JARVIS")
        self.geometry("400x650")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")

        # --- INIT VARIABLES ---
        # Initialize these FIRST to prevent AttributeError later
        self.model = None 
        self.is_listening = False
        init_error = None

        # --- SETUP AI ---
        try:
            genai.configure(api_key=GENAI_KEY)
            
            # Try initializing with Google Search Tools
            try:
                tools = [{"google_search": {}}]
                self.model = genai.GenerativeModel('gemini-2.5-flash', tools=tools)
            except Exception as e:
                print(f"Tool Init Failed (Falling back to standard): {e}")
                # Fallback: Standard model without tools if search fails
                self.model = genai.GenerativeModel('gemini-2.5-flash')
                
        except Exception as e:
            print(f"Critical AI Init Error: {e}")
            init_error = str(e)

        # --- UI SETUP ---
        self.label = ctk.CTkLabel(self, text="PROJECT JARVIS", font=("Courier New", 24, "bold"), text_color="#00ff41")
        self.label.pack(pady=20)

        self.status_label = ctk.CTkLabel(self, text="SYSTEM ONLINE", font=("Arial", 16, "bold"), text_color="#555555")
        self.status_label.pack(pady=10)

        self.log_box = ctk.CTkTextbox(self, width=350, height=350, text_color="#00ff41")
        self.log_box.pack(pady=10)
        
        self.log("System Initialized.")
        if init_error:
            self.log(f"WARNING: AI Failed to Load. {init_error}")
        elif self.model:
            self.log("AI Brain: Online")

        self.listen_btn = ctk.CTkButton(self, text="START LISTENING", command=self.toggle_listening, width=200, height=50, fg_color="#004411", hover_color="#00ff41")
        self.listen_btn.pack(pady=20)

        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 1000 
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.6 

    def log(self, message):
        self.log_box.insert("end", f"> {message}\n")
        self.log_box.see("end")

    def toggle_listening(self):
        if not self.is_listening:
            self.is_listening = True
            self.listen_btn.configure(text="STOP LISTENING", fg_color="#ff0000")
            self.status_label.configure(text="LISTENING...", text_color="#00ff41")
            
            self.log("Calibrating mic...")
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            
            threading.Thread(target=self.background_listener, daemon=True).start()
        else:
            self.is_listening = False
            self.listen_btn.configure(text="START LISTENING", fg_color="#004411")
            self.status_label.configure(text="STANDBY MODE", text_color="#555555")

    def background_listener(self):
        while self.is_listening:
            with sr.Microphone() as source:
                try:
                    audio = self.recognizer.listen(source, timeout=2, phrase_time_limit=4)
                    try:
                        text = self.recognizer.recognize_google(audio).lower()
                        if "jarvis" in text:
                            self.activate_agent(text)
                    except sr.UnknownValueError:
                        pass
                    except Exception as e:
                        print(f"Recognition Error: {e}")
                except:
                    continue 

    def clean_voice_command(self, text):
        text = text.lower()
        text = text.replace(" dot py", ".py").replace(" dot pi", ".py")
        text = text.replace(" dot js", ".js").replace(" dot java", ".java")
        text = text.replace(" dot txt", ".txt").replace(" dot com", ".com")
        text = text.replace(" underscore ", "_").replace(" dash ", "-")
        return text

    def activate_agent(self, full_text):
        self.status_label.configure(text="PROCESSING...", text_color="#ffff00")
        speak("Yes?") 
        
        command = full_text.lower().replace("jarvis", "").strip()
        
        if not command:
            self.log("Listening for command...")
            with sr.Microphone() as source:
                try:
                    audio = self.recognizer.listen(source, timeout=8, phrase_time_limit=10)
                    command = self.recognizer.recognize_google(audio).lower()
                except:
                    speak("I didn't catch that.")
                    self.status_label.configure(text="LISTENING...", text_color="#00ff41")
                    return

        command = self.clean_voice_command(command)
        
        self.log(f"User: {command}")
        self.process_command(command)
        
        time.sleep(1)
        if self.is_listening:
            self.status_label.configure(text="LISTENING...", text_color="#00ff41")

    def process_command(self, command):
        threading.Thread(target=self.run_ai, args=(command,)).start()

    def run_ai(self, command):
        if not self.model:
            self.after(0, self.log, "Error: AI Model not loaded. Check API Key.")
            speak("My AI brain is offline.")
            return

        if any(x in command.lower() for x in ["look", "see", "screen"]):
            self.handle_vision(command)
            return

        prompt = f"""
        You are Jarvis. Be concise.
        USER: "{command}"
        
        Return JSON.
        Actions: "open", "search", "media", "delete", "system", "clipboard", "write_code", "chat".
        
        RULES:
        - If user asks a question, use "chat".
        - If user says "open [file] in vs code", set target="vscode:[file]".
        
        Example: {{"action": "chat", "target": "I am fine."}}
        """
        try:
            response = self.model.generate_content(prompt)
            text = response.text.replace("```json", "").replace("```", "").strip()
            
            try:
                data = json.loads(text)
            except:
                data = {"action": "chat", "target": text}

            action = data.get("action")
            target = data.get("target")
            
            # Execute Action
            if action == "chat":
                self.after(0, self.log, f"Jarvis: {target}")
                speak(target)
            elif action == "open":
                self.after(0, self.log, f"Opening {target}")
                old_skills.open_app(target)
            elif action == "search":
                use_vscode = False
                if target.startswith("vscode:"):
                    use_vscode = True
                    target = target.replace("vscode:", "")
                self.after(0, self.log, f"Searching {target}...")
                result = old_skills.search_file(target, open_in_vscode=use_vscode)
                self.after(0, self.log, f"Result: {result}")
            elif action == "write_code":
                if "|" in target:
                    parts = target.split("|")
                    filename = parts[0]
                    folder = parts[1] if len(parts) > 1 and parts[1].strip() else None
                    content = "|".join(parts[2:]) if len(parts) > 2 else ""
                    if not content and len(parts) == 2:
                         content = parts[1]
                         folder = None
                    self.after(0, self.log, f"Jarvis: Writing {filename}...")
                    result = old_skills.create_code_file(filename, content, target_folder=folder)
                    self.after(0, self.log, f"Jarvis: {result}")
                else:
                    speak("Code generation failed format.")
            elif action == "media":
                old_skills.control_media(target)
            elif action == "system":
                res = system_ops.get_system_status(target)
                self.after(0, self.log, res)
            elif action == "clipboard":
                res = system_ops.read_clipboard()
                self.after(0, self.log, res[:100])
                speak(res[:200])

        except Exception as e:
            self.after(0, self.log, f"Error: {e}")
            speak("I encountered an error.")
        
        if not self.is_listening:
            self.reset_ui()

    def handle_vision(self, user_question):
        speak("Taking a look...")
        try:
            screenshot = ImageGrab.grab()
            prompt = ["Analyze this.", user_question, screenshot]
            response = self.model.generate_content(prompt)
            answer = response.text
            self.after(0, self.log, f"Jarvis: {answer[:100]}...")
            speak(answer)
        except Exception as e:
            print(e)

    def reset_ui(self):
        self.listen_btn.configure(state="normal", text="LISTEN")
        self.after(0, lambda: self.status_label.configure(text="SYSTEM ONLINE", text_color="#ffffff"))

if __name__ == "__main__":
    app = JarvisApp()
    app.mainloop()