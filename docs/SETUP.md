# Installation and Setup Guide for Jarvis Voice Module

## Prerequisites Check

Before installing, verify:

```powershell
# Check Python version (needs 3.9+)
python --version

# Check if NVIDIA GPU is available
nvidia-smi

# Check CUDA version (needs 11.x or 12.x)
nvcc --version
```

## Step-by-Step Installation

### 1. Install Python Dependencies

```bash
cd f:\voice-module
pip install -r requirements.txt
```

### 2. Install PyTorch with CUDA Support

For CUDA 12.1:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

For CUDA 11.8:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

For CPU only (not recommended):
```bash
pip install torch torchvision torchaudio
```

### 3. Install Piper TTS

**Windows**:
1. Download latest release from: https://github.com/rhasspy/piper/releases
2. Extract `piper.exe` to a permanent location (e.g., `C:\Program Files\Piper\`)
3. Add to PATH:
   ```powershell
   $env:Path += ";C:\Program Files\Piper"
   # Make permanent:
   [Environment]::SetEnvironmentVariable("Path", $env:Path, "Machine")
   ```
4. Download a voice model:
   ```powershell
   # Example: Download en_US-lessac-medium
   Invoke-WebRequest -Uri "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx" -OutFile "en_US-lessac-medium.onnx"
   Invoke-WebRequest -Uri "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json" -OutFile "en_US-lessac-medium.onnx.json"
   ```

**Linux/macOS**:
```bash
# Install via pip
pip install piper-tts

# Or download binary
wget https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_linux_x86_64.tar.gz
tar -xzf piper_linux_x86_64.tar.gz
sudo mv piper/piper /usr/local/bin/
```

### 4. Install PyAudio

**Windows**:
```bash
pip install pipwin
pipwin install pyaudio
```

If that fails, download wheel from: https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio

**Linux**:
```bash
sudo apt-get install portaudio19-dev python3-pyaudio
pip install pyaudio
```

**macOS**:
```bash
brew install portaudio
pip install pyaudio
```

### 5. Verify Installation

```python
# test_installation.py
import torch
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"CUDA version: {torch.version.cuda}")
    print(f"GPU: {torch.cuda.get_device_name(0)}")

# Test imports
from wake_engine import WakeWordEngine
from stt_service import STTService
from tts_service import TTSService
print("✅ All modules imported successfully!")
```

Run with:
```bash
python test_installation.py
```

## First Run

### Quick Test

```bash
python main.py
```

This will:
1. Download openWakeWord models (first run only)
2. Download Silero VAD model (first run only)
3. Download faster-whisper model (first run only)
4. Start listening for "Hey Jarvis"

### Individual Component Tests

**Test Wake Word**:
```bash
python wake_engine.py
```
Say "Hey Jarvis" and watch for detection.

**Test STT**:
```bash
python stt_service.py
```
Speak after the prompt and see transcription.

**Test TTS**:
```bash
python tts_service.py
```
You should hear Jarvis speak.

## Common Issues

### Issue: `ModuleNotFoundError: No module named 'openwakeword'`
**Solution**: 
```bash
pip install openwakeword
```

### Issue: `RuntimeError: CUDA out of memory`
**Solution**: Use smaller model or int8 quantization
```python
stt = STTService(
    model_size="distil-small.en",  # Smaller model
    compute_type="int8"  # Lower precision
)
```

### Issue: `FileNotFoundError: piper`
**Solution**: Ensure Piper is in PATH or specify full path:
```python
tts = TTSService(
    model_path=r"C:\full\path\to\en_US-lessac-medium.onnx"
)
```

### Issue: Wake word not detecting
**Solution**: 
- Lower threshold: `WakeWordEngine(threshold=0.3)`
- Check microphone input level
- Try speaking louder/clearer

### Issue: Poor transcription quality
**Solution**: 
- Use larger model: `model_size="distil-large-v2"`
- Adjust VAD settings in `stt_service.py`
- Check microphone quality

## Performance Tuning

### For Low-End GPUs (<6GB VRAM)
```python
stt = STTService(
    model_size="distil-small.en",
    compute_type="int8"
)
```

### For High-End GPUs (>8GB VRAM)
```python
stt = STTService(
    model_size="distil-large-v2",
    compute_type="float16"
)
```

### For CPU Only
```python
stt = STTService(
    model_size="tiny.en",
    device="cpu",
    compute_type="int8"
)
```

## Next Steps

1. ✅ Verify all components work individually
2. ✅ Test end-to-end with `main.py`
3. ✅ Review `system_prompts.py` for router logic
4. 🔧 Integrate with your LLM/router backend
5. 🔧 Implement tool execution layer
6. 🚀 Deploy and test!

## Support

For issues:
- Check logs with `logging.DEBUG` level
- Verify GPU utilization with `nvidia-smi`
- Test microphone with Windows Sound Recorder
- Review GitHub issues for each component library
