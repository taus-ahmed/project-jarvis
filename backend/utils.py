import pyttsx3
import re

def clean_text_for_speech(text):
    text = re.sub(r'\*+', '', text) # Remove **
    text = text.replace('`', '')
    text = text.replace('#', '')
    text = " ".join(text.split())
    return text

def speak(text):
    try:
        # Initialize engine locally to prevent thread hanging
        engine = pyttsx3.init()
        engine.setProperty('rate', 180)
        clean = clean_text_for_speech(text)
        engine.say(clean)
        engine.runAndWait()
    except Exception as e:
        print(f"Voice Error: {e}")

def normalize(text):
    """Removes special chars: 'host.py' -> 'hostpy'"""
    return "".join(char for char in text if char.isalnum()).lower()