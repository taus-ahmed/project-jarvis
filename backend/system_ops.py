import psutil
import pyperclip
from utils import speak

def get_system_status(target):
    """Checks Battery, CPU, and RAM."""
    speak("Checking system vitals...")
    
    status_report = []
    
    # 1. BATTERY
    try:
        battery = psutil.sensors_battery()
        if battery:
            plugged = "plugged in" if battery.power_plugged else "on battery"
            status_report.append(f"Battery is at {battery.percent}% and {plugged}.")
        else:
            status_report.append("Desktop power connected.")
    except:
        status_report.append("Could not read battery stats.")

    # 2. CPU
    cpu_usage = psutil.cpu_percent(interval=1)
    status_report.append(f"CPU usage is {cpu_usage}%.")

    # 3. MEMORY
    ram = psutil.virtual_memory()
    status_report.append(f"RAM usage is {ram.percent}%.")

    final_report = " ".join(status_report)
    speak(final_report)
    return final_report

def read_clipboard():
    """Reads whatever text is currently copied."""
    try:
        content = pyperclip.paste()
        if not content:
            speak("Your clipboard is empty.")
            return "Empty clipboard."
        
        return content
    except:
        speak("I couldn't read the clipboard.")
        return "Error reading clipboard."