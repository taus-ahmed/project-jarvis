# Setup Guide for Production TTS with GPU Acceleration

## Prerequisites

✅ You have `onnxruntime-gpu` installed  
✅ You have NVIDIA GPU with CUDA support  
✅ Piper executable is installed and in PATH

## Step 1: Create Models Directory

```powershell
# From F:\voice-module
New-Item -ItemType Directory -Force -Path "models"
cd models
```

## Step 2: Download Voice Model (en_US-ryan-high)

### Option A: Direct Download (Recommended)

```powershell
# Download Ryan voice (high quality, ~63MB)
Invoke-WebRequest -Uri "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/high/en_US-ryan-high.onnx" -OutFile "en_US-ryan-high.onnx"

Invoke-WebRequest -Uri "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/high/en_US-ryan-high.onnx.json" -OutFile "en_US-ryan-high.onnx.json"
```

### Option B: Alternative Voices

If you prefer a different voice:

```powershell
# Amy (female, medium quality, faster)
Invoke-WebRequest -Uri "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx" -OutFile "en_US-amy-medium.onnx"
Invoke-WebRequest -Uri "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json" -OutFile "en_US-amy-medium.onnx.json"

# Lessac (neutral, medium quality)
Invoke-WebRequest -Uri "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx" -OutFile "en_US-lessac-medium.onnx"
Invoke-WebRequest -Uri "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json" -OutFile "en_US-lessac-medium.onnx.json"
```

### Option C: Browse All Voices

Visit: https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_US

Quality levels:
- **low**: ~12MB, fast but robotic
- **medium**: ~25MB, balanced
- **high**: ~60MB, best quality

## Step 3: Verify Installation

```powershell
# Check files exist
Get-ChildItem models/*.onnx
Get-ChildItem models/*.json

# Test Piper directly
cd ..
piper --model models/en_US-ryan-high.onnx --output_file test.wav --text "Testing Jarvis voice module with GPU acceleration."

# Play test.wav to verify
```

## Step 4: Configure for GPU (CUDA)

The TTSService will automatically use CUDA if:
1. `onnxruntime-gpu` is installed ✅
2. `use_cuda=True` is set ✅
3. Piper binary supports CUDA (most do)

**Note**: Current Piper releases may not expose a `--cuda` flag directly. The ONNX runtime will use CUDA automatically through onnxruntime-gpu. If you see performance issues, check:

```powershell
# Verify onnxruntime-gpu is installed
pip show onnxruntime-gpu

# If not:
pip uninstall onnxruntime  # Remove CPU version first
pip install onnxruntime-gpu
```

## Step 5: Test the Integration

### Test TTS Service Only

```powershell
python -c "
import asyncio
from tts_service import TTSService

async def test():
    tts = TTSService(
        model_path='models/en_US-ryan-high.onnx',
        use_cuda=True
    )
    tts.speak_async('Hello from Jarvis with GPU acceleration!')
    tts.wait_until_done()
    tts.shutdown()

asyncio.run(test())
"
```

### Test Full Integration

```powershell
python jarvis_integration.py
```

This will test:
- ✅ STT (faster-whisper)
- ✅ TTS (Piper with GPU)
- ✅ Queue-based playback
- ✅ Barge-in capability

## Architecture Overview

```
┌─────────────────────────────────────────┐
│           User Speaks                   │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│     STT Service (faster-whisper)        │
│     - GPU accelerated                   │
│     - VAD auto-detection                │
└──────────────┬──────────────────────────┘
               │ Transcription
               ▼
┌─────────────────────────────────────────┐
│     Brain/Router (Your LLM)             │
│     - Intent classification             │
│     - JSON output                       │
└──────────────┬──────────────────────────┘
               │ Intent + Entities
               ▼
┌─────────────────────────────────────────┐
│     Tool Execution                      │
│     - FILE_SYSTEM                       │
│     - BROWSER                           │
│     - CHAT                              │
└──────────────┬──────────────────────────┘
               │ Response Text
               ▼
┌─────────────────────────────────────────┐
│     TTS Service (Piper)                 │
│     - GPU accelerated (CUDA)            │
│     - Queue-based playback              │
│     - Barge-in support                  │
│     - Background worker thread          │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│         Audio Output                    │
└─────────────────────────────────────────┘
```

## Barge-In Flow

```
TTS is speaking...
    │
    ├─ VAD detects user speech
    │
    ├─ tts.stop_speaking() called
    │  - Sets should_stop flag
    │  - Clears speech queue
    │  - Stops audio playback
    │
    ├─ STT captures new input
    │
    └─ New response queued to TTS
```

## Performance Expectations

With GPU acceleration:
- **TTS Synthesis**: 50-150ms (depends on text length)
- **TTS Queue**: Instant (non-blocking)
- **Barge-in Response**: < 100ms
- **Total Latency**: 200-300ms for short phrases

## Troubleshooting

### Issue: "Piper executable not found"
```powershell
# Verify Piper in PATH
piper --version

# If not found, add to PATH
$env:Path += ";C:\path\to\piper"
```

### Issue: "Model not found"
```powershell
# Check model path
Test-Path models/en_US-ryan-high.onnx
# Should return: True
```

### Issue: "No CUDA acceleration"
```powershell
# Check onnxruntime-gpu
python -c "import onnxruntime; print(onnxruntime.get_available_providers())"
# Should include: CUDAExecutionProvider
```

### Issue: TTS is slow
- Verify GPU is being used: `nvidia-smi` while running
- Try medium quality model instead of high
- Check `length_scale` parameter (lower = faster)

## Next Steps

1. ✅ Test TTS service independently
2. ✅ Test full integration with `jarvis_integration.py`
3. ✅ Replace mock `get_intent()` with your LLM router
4. ✅ Replace mock `execute_intent()` with your tool execution
5. ✅ Add wake word detection (optional, can use hotkey)
6. 🚀 Deploy!

## Example Integration with Your Router

```python
async def get_intent(self, user_input: str) -> dict:
    """Call your LLM router."""
    from system_prompts import get_router_prompt
    
    # Your LLM API call
    response = await your_llm.chat(
        system=get_router_prompt(),
        messages=[{"role": "user", "content": user_input}],
        temperature=0.3,
        max_tokens=500
    )
    
    # Parse JSON response
    intent_data = json.loads(response)
    return intent_data
```

## Questions?

Check the files:
- `tts_service.py` - TTS implementation with GPU and queue
- `jarvis_integration.py` - Full integration example
- `main.py` - Main entry point with wake word
- `system_prompts.py` - Router prompt for intent classification
