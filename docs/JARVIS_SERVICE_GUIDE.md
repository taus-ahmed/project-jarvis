# Jarvis Service - Production Assistant Guide

## Overview

`jarvis_service.py` is the **production-ready** version of your voice assistant with a state machine architecture that keeps Jarvis awake for 5 seconds after each interaction.

## Key Features

✅ **State Machine Architecture**
- `IDLE`: Low-power mode, listening only for wake word
- `ACTIVE`: 5-second window for follow-up commands (no wake word needed)
- `LISTENING`: Recording user voice with VAD auto-detection
- `PROCESSING`: Transcribing and routing to LLM
- `SPEAKING`: TTS playing response

✅ **Persistent Interaction**
- After activation, stays awake for 5 seconds
- Each new command resets the 5-second timer
- Automatically returns to IDLE if no speech detected

✅ **Barge-in Support** (via TTS queue)
- Interrupt Jarvis mid-sentence by speaking
- TTS queue automatically clears on new input

✅ **LLM Integration Ready**
- Mock brain for testing (keyword matching)
- Easy integration point for real LLM API
- Uses `system_prompts.py` for router logic

## Architecture Comparison

| File | Purpose | Behavior |
|------|---------|----------|
| `test_voice.py` | STT testing only | Single transcription, exits |
| `jarvis_integration.py` | Pipeline demo | One interaction, exits |
| `main.py` | Original design | Wake word → command → exit |
| **`jarvis_service.py`** | **Production service** | **Persistent with 5s window** |

## State Flow Diagram

```
┌─────────────────────────────────────────────────┐
│                   START                         │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
         ┌───────────────┐
         │     IDLE      │◄──────────────┐
         │ (Wake Word)   │               │
         └───────┬───────┘               │
                 │                       │
          Wake detected                  │
                 │                       │
                 ▼                       │
         ┌───────────────┐               │
         │    ACTIVE     │               │
         │ (5s window)   │◄──────┐       │
         └───────┬───────┘       │       │
                 │               │       │
          User speaks            │       │
                 │               │       │
                 ▼               │       │
         ┌───────────────┐       │       │
         │  LISTENING    │       │       │
         │ (Recording)   │       │       │
         └───────┬───────┘       │       │
                 │               │       │
          Speech ends            │       │
                 │               │       │
                 ▼               │       │
         ┌───────────────┐       │       │
         │  PROCESSING   │       │       │
         │ (STT + LLM)   │       │       │
         └───────┬───────┘       │       │
                 │               │       │
          Response ready         │       │
                 │               │       │
                 ▼               │       │
         ┌───────────────┐       │       │
         │   SPEAKING    │       │       │
         │ (TTS output)  │       │       │
         └───────┬───────┘       │       │
                 │               │       │
                 └───────────────┘       │
                  (Reset 5s timer)       │
                                         │
                  Timeout (5s) ──────────┘
```

## Usage

### Basic Start

```bash
python jarvis_service.py
```

### With Virtual Environment

```bash
.venv\Scripts\activate
python jarvis_service.py
```

## Configuration

Edit the `main()` function in `jarvis_service.py`:

```python
jarvis = JarvisService(
    use_cuda=True,                                    # GPU acceleration
    tts_model_path="models/en_US-ryan-high.onnx",   # Your TTS voice
    active_window_seconds=5.0,                       # Follow-up window
    llm_api_url="http://localhost:8000/chat"        # Your LLM API
)
```

## Integrating Your LLM

### Step 1: Replace Mock Brain

Find the `_get_llm_response()` method in `jarvis_service.py` (around line 155):

```python
async def _get_llm_response(self, user_input: str) -> Dict[str, Any]:
    """Route user input through LLM to get intent and response."""
    
    # Replace this mock code with your actual LLM API call
    if self.llm_api_url:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            payload = {
                "messages": [
                    {
                        "role": "system", 
                        "content": get_router_prompt()
                    },
                    {
                        "role": "user", 
                        "content": user_input
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 500
            }
            
            async with session.post(self.llm_api_url, json=payload) as resp:
                llm_response = await resp.json()
                
                # Parse LLM JSON response
                return json.loads(llm_response["content"])
    
    # Fallback to mock
    return self._mock_response(user_input)
```

### Step 2: Connect Tool Execution

Find the `_execute_action()` method (around line 210):

```python
async def _execute_action(self, action: Optional[Dict[str, Any]]):
    """Execute system actions based on intent."""
    
    if not action:
        return
    
    action_type = action.get("type")
    
    # Add your tool integrations here
    if action_type == "FILE_SYSTEM":
        # Call your file system handler
        path = action.get("path")
        operation = action.get("operation")
        await your_file_system_handler(path, operation)
        
    elif action_type == "BROWSER":
        query = action.get("query")
        await your_browser_handler(query)
        
    elif action_type == "SYSTEM":
        command = action.get("command")
        await your_system_handler(command)
```

## Expected LLM Response Format

Your LLM should return JSON matching this structure:

```json
{
    "intent": "FILE_SYSTEM",
    "response": "I'll open that folder for you.",
    "action": {
        "type": "FILE_SYSTEM",
        "operation": "open",
        "path": "C:\\Users\\Documents"
    }
}
```

Supported intents (from `system_prompts.py`):
- `CHAT`: General conversation
- `FILE_SYSTEM`: File/folder operations
- `BROWSER`: Web searches, URLs
- `SYSTEM`: System commands
- `WINDOW`: Window management
- `APPLICATION`: App launching
- `CLIPBOARD`: Copy/paste operations
- `MEDIA`: Media control

## Wake Word Integration

Currently uses **simulated wake word** (press ENTER). To integrate real wake word:

### Option 1: OpenWakeWord (when models available)

```python
from wake_engine import WakeWordEngine

async def _wait_for_wake_word(self):
    """Real wake word detection."""
    wake_engine = WakeWordEngine(threshold=0.5)
    
    # Blocking wait for wake word
    detected = await wake_engine.listen_for_wake_async()
    
    if detected:
        logger.info("🎙️ 'Hey Jarvis' detected!")
```

### Option 2: Porcupine (commercial, very accurate)

```bash
pip install pvporcupine
```

```python
import pvporcupine

wake = pvporcupine.create(
    access_key="YOUR_PICOVOICE_KEY",
    keywords=["jarvis"]
)
```

### Option 3: Hotkey Trigger (simplest)

```python
from pynput import keyboard

def on_press(key):
    if key == keyboard.Key.f12:  # F12 = wake
        asyncio.create_task(self._active_loop())
```

## Testing

### 1. Test STT Only
```bash
python test_voice.py
```

### 2. Test Full Pipeline (one-shot)
```bash
python jarvis_integration.py
```

### 3. Test Service (persistent)
```bash
python jarvis_service.py
```

## Example Interactions

### Single Command
```
[Press ENTER]
Jarvis: "Yes?"
You: "What time is it?"
Jarvis: "The current time is 3:45 PM."
[5-second window starts]
[Timeout after 5s]
[Back to IDLE]
```

### Follow-up Commands (Within 5 seconds)
```
[Press ENTER]
Jarvis: "Yes?"
You: "What time is it?"
Jarvis: "The current time is 3:45 PM."
[5-second window - timer reset]
You: "And the date?"
Jarvis: "Today is January 5th, 2026."
[5-second window - timer reset]
You: "Thank you"
Jarvis: "You're welcome! Anything else?"
[5-second window]
[Timeout after 5s]
[Back to IDLE]
```

## Troubleshooting

### Issue: "TTS keeps saying 'Yes?' but doesn't transcribe"
- **Cause**: VAD not detecting speech start
- **Fix**: Speak louder or adjust VAD threshold in `stt_service.py`

### Issue: "5-second window too short"
- **Fix**: Increase `active_window_seconds` parameter:
  ```python
  jarvis = JarvisService(active_window_seconds=10.0)
  ```

### Issue: "Jarvis exits immediately after command"
- **Cause**: Using `jarvis_integration.py` instead of `jarvis_service.py`
- **Fix**: Run `python jarvis_service.py`

### Issue: "Wake word not working"
- **Current**: Wake word models unavailable (HTTP 404)
- **Temporary**: Use ENTER key simulation
- **Future**: Download working wake word models or use Porcupine

## Performance Optimization

### Reduce Latency
1. Use GPU for both STT and TTS:
   ```python
   jarvis = JarvisService(use_cuda=True)
   ```

2. Use faster Whisper model:
   - Change in `stt_service.py` init: `model_size="base.en"`

3. Reduce TTS quality for speed:
   - Use `-low` or `-medium` Piper voices instead of `-high`

### Reduce Memory Usage
1. Use CPU mode:
   ```python
   jarvis = JarvisService(use_cuda=False)
   ```

2. Use int8 quantization (already enabled)

## Next Steps

1. ✅ Run `python jarvis_service.py` to test persistent service
2. ⬜ Integrate your LLM API in `_get_llm_response()`
3. ⬜ Connect tool execution in `_execute_action()`
4. ⬜ Add real wake word when models available
5. ⬜ Deploy as Windows service (optional)

## Files Reference

- **`jarvis_service.py`** - Production service (use this)
- **`jarvis_integration.py`** - Demo script (single interaction)
- **`main.py`** - Original design (being deprecated)
- **`test_voice.py`** - STT testing only
- **`stt_service.py`** - Speech-to-text service
- **`tts_service.py`** - Text-to-speech service
- **`system_prompts.py`** - Router prompts for LLM
- **`wake_engine.py`** - Wake word detection (pending models)

## Support

For issues, check:
1. Virtual environment activated: `.venv\Scripts\activate`
2. All dependencies installed: `pip install -r requirements.txt`
3. TTS model exists: `models/en_US-ryan-high.onnx`
4. Microphone permissions enabled
5. Audio device detected: `python -c "import pyaudio; print('OK')"`
