# Jarvis Voice Module

Desktop Large Action Model (LAM) voice interface with GPU-accelerated processing.

## Features

- ⚡ **Wake Word Detection**: CPU-based "Hey Jarvis" detection using openWakeWord
- 🎤 **Speech Recognition**: GPU-accelerated faster-whisper with distil-medium model (sub-1s latency)
- 🔊 **Text-to-Speech**: Piper TTS with sub-200ms latency
- 🎯 **VAD Integration**: Silero VAD for automatic speech endpoint detection
- 🔄 **Async Architecture**: Non-blocking asyncio design

## Requirements

- Python 3.9+
- NVIDIA GPU with CUDA support (optional, but recommended for STT)
- Windows/Linux/macOS

## Installation

1. **Clone and setup**:
```bash
cd f:\voice-module
pip install -r requirements.txt
```

2. **Install Piper TTS** (download binary):
   - Windows: Download from [Piper Releases](https://github.com/rhasspy/piper/releases)
   - Extract `piper.exe` and add to PATH
   - Download a voice model (e.g., `en_US-lessac-medium.onnx`)

3. **Install PyTorch with CUDA** (for GPU acceleration):
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

## Usage

### Basic Usage

```python
import asyncio
from main import JarvisVoiceModule

async def run():
    jarvis = JarvisVoiceModule(
        use_cuda=True,
        wake_threshold=0.5,
        tts_model_path="en_US-lessac-medium.onnx"
    )
    await jarvis.run()

asyncio.run(run())
```

### Direct Component Usage

**Wake Word Detection**:
```python
from wake_engine import WakeWordEngine

async def on_wake():
    print("Jarvis activated!")

engine = WakeWordEngine(threshold=0.5)
await engine.start_listening_async(on_wake)
```

**Speech-to-Text**:
```python
from stt_service import STTService

stt = STTService(device="cuda", compute_type="int8")
text = await stt.transcribe_stream(duration_seconds=10)
print(f"Transcription: {text}")
```

**Text-to-Speech**:
```python
from tts_service import TTSService

tts = TTSService(model_path="en_US-lessac-medium.onnx")
await tts.speak("Hello, I am Jarvis!")
```

## Architecture

```
┌─────────────────────┐
│   Wake Word (CPU)   │  ← Always listening for "Hey Jarvis"
└──────────┬──────────┘
           │ Triggers
           ▼
┌─────────────────────┐
│   STT (GPU/CUDA)    │  ← Transcribes user speech with VAD
└──────────┬──────────┘
           │ Text
           ▼
┌─────────────────────┐
│  Router/LLM Logic   │  ← Your intent classifier (external)
└──────────┬──────────┘
           │ Response
           ▼
┌─────────────────────┐
│   TTS (CPU/GPU)     │  ← Speaks response
└─────────────────────┘
```

## Files

- `wake_engine.py`: OpenWakeWord integration for "Hey Jarvis" detection
- `stt_service.py`: Faster-whisper STT with Silero VAD
- `tts_service.py`: Piper TTS for ultra-fast voice synthesis
- `system_prompts.py`: Router system prompts with strict JSON output format
- `main.py`: Main orchestration and example usage
- `requirements.txt`: Python dependencies

## Router System Prompt

The router uses a strict JSON-only output format to classify user intent:

```json
{
  "intent": "FILE_SYSTEM | BROWSER | CHAT | ...",
  "confidence": 0.95,
  "entities": {
    "primary_target": "filename.txt",
    "parameters": {}
  },
  "reasoning": "Brief explanation",
  "requires_clarification": false
}
```

**Intent Types**:
- `FILE_SYSTEM`: File operations
- `BROWSER`: Web browsing
- `APPLICATION`: App control
- `SYSTEM`: System operations
- `CHAT`: General conversation
- `MULTIMODAL`: Vision tasks
- `AUTOMATION`: Multi-step workflows
- `CLARIFICATION`: Ambiguous input

See `system_prompts.py` for the complete router prompt specification.

## Performance

- **Wake Word**: ~20ms latency per chunk (CPU)
- **STT**: <1s transcription (GPU with int8 quantization)
- **TTS**: <200ms synthesis (Piper)
- **Total**: ~2-3s end-to-end response time

## GPU Optimization

For best performance on NVIDIA GPUs:

1. Use `distil-medium.en` Whisper model (balanced speed/accuracy)
2. Enable `int8` quantization for 2x speedup
3. Ensure CUDA toolkit is properly installed
4. Monitor GPU memory with `nvidia-smi`

## Troubleshooting

**No wake word model found**:
- OpenWakeWord downloads models automatically on first run
- Check internet connection

**CUDA out of memory**:
- Reduce Whisper model size: `distil-small.en` or `tiny.en`
- Use `compute_type="int8_float16"` for lower memory usage

**Piper not found**:
- Ensure `piper` or `piper.exe` is in your system PATH
- Test with: `piper --version`

**Poor transcription accuracy**:
- Adjust VAD threshold in `stt_service.py`
- Use `distil-large-v2` for better accuracy (slower)
- Ensure microphone quality is good

## Integration with Router/LLM

Replace the `process_command()` method in `main.py` with your LLM integration:

```python
async def process_command(self, text: str):
    # 1. Send to router with system prompt
    router_response = await your_llm_api.chat(
        system=get_router_prompt(),
        user=text
    )
    
    # 2. Parse JSON intent
    intent_data = json.loads(router_response)
    
    # 3. Execute appropriate tool
    if intent_data["intent"] == "FILE_SYSTEM":
        result = await your_file_tool.execute(intent_data)
    # ... handle other intents
    
    # 4. Speak response
    await self.tts_service.speak(result)
```

## License

MIT License - See LICENSE file for details

## Credits

- [OpenWakeWord](https://github.com/dscripka/openWakeWord)
- [faster-whisper](https://github.com/guillaumekln/faster-whisper)
- [Silero VAD](https://github.com/snakers4/silero-vad)
- [Piper TTS](https://github.com/rhasspy/piper)
