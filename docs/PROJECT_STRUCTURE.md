# Jarvis Voice Assistant - Project Structure

## 🎯 Core Files (Essential)

### Python Scripts
- **run_jarvis.py** - Main entry point, orchestrates all services
- **wake_engine.py** - Wake word detection using openWakeWord
- **stt_service.py** - Speech-to-text using faster-whisper
- **tts_service.py** - Text-to-speech using Piper TTS
- **system_prompts.py** - LLM system prompts and router logic

### Configuration
- **requirements.txt** - Python dependencies

### Models & Assets
- **models/** - Piper TTS voice models (ONNX format)
- **piper/** - Piper TTS executable and espeak-ng data

## 📚 Documentation Files

### Setup Guides
- **README.md** - Project overview
- **SETUP.md** - Installation instructions
- **TTS_SETUP.md** - Text-to-speech setup
- **WAKE_WORD_SETUP.md** - Wake word configuration

### Implementation Guides
- **QUICK_START.md** - Quick reference guide
- **REFACTORING_GUIDE.md** - Detailed refactoring documentation
- **TTS_IMPLEMENTATION.md** - TTS implementation details
- **LLM_INTEGRATION.md** - LLM integration guide
- **JARVIS_SERVICE_GUIDE.md** - Service architecture guide
- **WAKE_WORD_REFACTORING.md** - Wake word refactoring details

### Status Documents
- **ARCHITECTURE.md** - System architecture overview
- **CHANGES.md** - Change log with code examples
- **COMPLETE.md** - Completion summary

## 🗑️ Cleaned Up (Removed)

### Test Files (All removed)
- test_wake_word.py
- test_wake_quick.py
- test_jarvis_wake.py
- test_full_flow.py
- test_direct.py
- test_load_order.py
- test_tts_shutdown.py
- test_minimal.py

### Debugging Tools (Removed)
- capture_error.py
- download_models.py

### Redundant Files (Removed)
- jarvis_service.py (replaced by run_jarvis.py)
- setup_wakeword.py (functionality integrated)

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run Jarvis
python run_jarvis.py

# 3. Say "Hey Mycroft" to activate
```

## 📂 File Sizes
- Total Python code: ~71 KB (5 files)
- Total documentation: ~93 KB (13 files)
- Models: ~11 MB (Piper voice models)
- Piper engine: ~45 MB (with espeak-ng data)

---

**Status:** ✅ Production Ready
**Last Cleaned:** January 6, 2026
