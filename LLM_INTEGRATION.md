# 🤖 JARVIS - Complete Setup Guide

## ✅ What's Working Now

Your Jarvis voice assistant is **fully functional** with:

1. ✅ **Speech-to-Text** - Faster-Whisper with Silero VAD
2. ✅ **Text-to-Speech** - Piper TTS with natural voice
3. ✅ **LLM Integration Ready** - Configure your API in `run_jarvis.py`
4. ✅ **Smart Pause Detection** - 1.5 second pause before stopping recording
5. ✅ **5-Second Follow-up Window** - Ask multiple questions without reactivating

## 🚀 Quick Start

### Run Jarvis:
```powershell
python run_jarvis.py
```

That's it! The system will:
1. Load all AI models
2. Wait for you to press ENTER (simulated wake word)
3. Say "Yes?" and listen for your command
4. Respond intelligently
5. Stay active for 5 seconds for follow-up questions

## 📋 Files You Need

**Core Files** (keep these):
- `run_jarvis.py` - **Main entry point** (run this!)
- `stt_service.py` - Speech recognition
- `tts_service.py` - Text-to-speech
- `system_prompts.py` - LLM prompts
- `wake_engine.py` - Wake word (currently disabled)
- `requirements.txt` - Dependencies
- `models/` - Voice models directory
- `piper/` - TTS executable directory

**Documentation** (reference):
- `README.md` - Project overview
- `JARVIS_SERVICE_GUIDE.md` - Technical details
- `LLM_INTEGRATION.md` - This guide

**Unnecessary Files** (deleted):
- ~~test_voice.py~~
- ~~test_jarvis.py~~
- ~~jarvis_integration.py~~
- ~~main.py~~
- ~~setup_tts.py~~
- ~~install_piper.py~~

## 🔧 Configure Your LLM

Edit `run_jarvis.py` lines 30-50:

### Option 1: OpenAI API
```python
class LLMConfig:
    USE_OPENAI = True
    OPENAI_API_KEY = "sk-your-api-key-here"
    OPENAI_MODEL = "gpt-4"
```

### Option 2: Local LLM (LM Studio, Ollama)
```python
class LLMConfig:
    USE_LOCAL_LLM = True
    LOCAL_LLM_URL = "http://localhost:1234/v1/chat/completions"
    LOCAL_LLM_MODEL = "your-model-name"
```

**To get LM Studio:**
1. Download from https://lmstudio.ai/
2. Install and download a model (e.g., "Llama 3.1" or "Mistral")
3. Click "Start Server" in LM Studio
4. Copy the URL (usually `http://localhost:1234/v1/chat/completions`)
5. Update `LOCAL_LLM_URL` in `run_jarvis.py`

### Option 3: Mock Mode (Current)
No configuration needed! Works out of the box with keyword responses:
- "What time is it?" → Real time
- "What's the date?" → Real date
- "Hello" → Greeting
- "Weather" → Weather check
- "Goodbye" → Exits

## 🎤 Wake Word Status

**Current:** Press ENTER to activate (simulated wake word)

**Why:** OpenWakeWord models have broken downloads

**Future Options:**
1. **Wait for fix** - OpenWakeWord team will fix model downloads
2. **Use Porcupine** - Commercial but very accurate
3. **Use hotkey** - Press F12 or a keyboard shortcut
4. **Skip it** - ENTER works fine for desktop use!

## 🎯 How to Use

### Basic Interaction:
```
1. Run: python run_jarvis.py
2. Wait for "Press ENTER to activate"
3. Press ENTER
4. Jarvis says "Yes?"
5. Speak your command (1.5s pause = done recording)
6. Jarvis responds with voice
7. You have 5 seconds to ask follow-up
8. Say "goodbye" or wait 5s to go back to sleep
```

### Example Session:
```
You: [Press ENTER]
Jarvis: "Yes?"
You: "What time is it?"
Jarvis: "The current time is 3:45 PM."
[5-second window active]
You: "And what's the date?"
Jarvis: "Today is Sunday, January 5th, 2026."
[5-second window active]
You: "Thank you"
Jarvis: "You're welcome! Anything else I can help with?"
[5-second window]
[Timeout...]
Jarvis: [Back to sleep, press ENTER to wake]
```

## ⚙️ Settings You Can Change

### In `run_jarvis.py`:

**Active Window Duration:**
```python
jarvis = Jarvis(active_window_seconds=5.0)  # Change to 10.0 for longer
```

**Pause Detection:**
```python
self.stt = STTService(
    min_silence_duration_ms=1500  # Current: 1.5s pause
                                    # Increase to 2000 for 2s pause
                                    # Decrease to 1000 for 1s pause
)
```

**LLM Response Length:**
```python
class LLMConfig:
    MAX_TOKENS = 500  # Increase for longer responses
    TEMPERATURE = 0.7  # 0.0 = precise, 1.0 = creative
```

## 🐛 Troubleshooting

### "No speech detected"
- **Cause:** Microphone not picking up voice or speaking too quietly
- **Fix:** Speak louder, check microphone in Windows Sound settings

### "Can't hear Jarvis speaking"
- **Cause:** Volume low or wrong audio output device
- **Fix:** Check Windows volume, ensure correct speakers/headphones selected

### "Recording stops too soon"
- **Cause:** Pause detection too sensitive
- **Fix:** Edit `stt_service.py` line 37: change `min_silence_duration_ms=1500` to `2000` or `2500`

### "LLM not responding intelligently"
- **Cause:** Still in mock mode
- **Fix:** Configure LLM in `run_jarvis.py` (see section above)

### "Wake word doesn't work"
- **Status:** Known issue, models unavailable
- **Fix:** Use ENTER key for now (works perfectly!)

## 📊 System Requirements

**Minimum:**
- Windows 10/11
- Python 3.8+
- 4GB RAM
- Microphone
- Speakers/Headphones

**Recommended:**
- NVIDIA GPU (for faster processing)
- 8GB+ RAM
- Good quality microphone

## 🎓 Next Steps

1. **Test it first:**
   ```powershell
   python run_jarvis.py
   ```

2. **Configure LLM** (optional but recommended):
   - Install LM Studio
   - Update `run_jarvis.py` with your API

3. **Customize responses:**
   - Edit `system_prompts.py` to change Jarvis's personality
   - Modify intents and responses

4. **Add tools** (advanced):
   - File system operations
   - Browser automation
   - System commands
   - See `system_prompts.py` for intent types

## 💡 Pro Tips

1. **Speak clearly** - No need to shout, but speak at normal conversation volume
2. **Wait for "Yes?"** - Make sure Jarvis acknowledges before speaking
3. **Pause naturally** - 1.5-second pause signals you're done talking
4. **Use follow-ups** - Take advantage of the 5-second window for related questions
5. **Say "goodbye"** - Clean exit vs letting it timeout

## 📞 Support

If something isn't working:
1. Check this guide's troubleshooting section
2. Verify all files are in place (see "Files You Need")
3. Ensure Python environment is activated: `.venv\Scripts\activate`
4. Check dependencies: `pip install -r requirements.txt`

## 🎉 You're Done!

Your Jarvis is ready to use. Just run:

```powershell
python run_jarvis.py
```

Press ENTER, speak your command, and enjoy your AI assistant!
