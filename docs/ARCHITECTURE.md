# 🏗️ Jarvis Architecture Overview

## System Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         JARVIS SYSTEM                            │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐
│   🎤 USER    │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│  1️⃣ WAKE WORD DETECTION (openWakeWord)                      │
│     • Continuous listening on CPU                            │
│     • Threshold: 0.5                                         │
│     • Detects: "Hey Jarvis"                                  │
│     • Latency: <500ms                                        │
└──────┬───────────────────────────────────────────────────────┘
       │ Wake word detected ✓
       ▼
┌──────────────────────────────────────────────────────────────┐
│  STATE MACHINE                                               │
│  ┌──────────┐  wake   ┌──────────┐                         │
│  │   IDLE   │────────>│  ACTIVE  │<────┐                   │
│  └──────────┘         └────┬─────┘     │                   │
│                             │ 5s window │                   │
│                             ▼           │                   │
│                       ┌────────────┐    │                   │
│                       │ LISTENING  │    │                   │
│                       └─────┬──────┘    │                   │
│                             │           │                   │
│                             ▼           │                   │
│                       ┌────────────┐    │                   │
│                       │ PROCESSING │    │                   │
│                       └─────┬──────┘    │                   │
│                             │           │                   │
│                             ▼           │                   │
│                       ┌────────────┐    │                   │
│                       │  SPEAKING  │────┘                   │
│                       └────────────┘                        │
└──────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│  2️⃣ SPEECH-TO-TEXT (faster-whisper + Silero VAD)           │
│     • Model: distil-medium.en                               │
│     • Device: Auto-detect (CUDA/CPU)                        │
│     • VAD Threshold: 0.6                                    │
│     • Min Silence: 800ms (47% faster than before)           │
│     • Latency: 1-2s (GPU) / 2-3s (CPU)                      │
└──────┬───────────────────────────────────────────────────────┘
       │ Transcribed text
       ▼
┌──────────────────────────────────────────────────────────────┐
│  3️⃣ LLM ROUTING (Ollama/LM Studio)                          │
│     • Endpoint: http://localhost:11434/v1/chat/completions  │
│     • Model: llama3.2 (configurable)                        │
│     • Output: Structured JSON                               │
│     {                                                        │
│       "intent": "CHAT|FILE_SYSTEM|BROWSER|...",             │
│       "response": "...",                                     │
│       "action": {...}                                        │
│     }                                                        │
│     • Fallback: Mock mode if unavailable                    │
│     • Latency: <1s (local)                                  │
└──────┬───────────────────────────────────────────────────────┘
       │ Structured JSON
       ▼
┌──────────────────────────────────────────────────────────────┐
│  4️⃣ MCP TOOL EXECUTION (Integration Point)                  │
│     • Input: LLM action object                              │
│     • Process: _execute_mcp_tools()                         │
│     • Actions:                                              │
│       - FILE_SYSTEM: file operations                        │
│       - BROWSER: web browsing                               │
│       - APPLICATION: app control                            │
│       - SYSTEM: system commands                             │
│     • Output: Tool result (merged with response)            │
│     • Status: Ready for integration (stub implemented)       │
└──────┬───────────────────────────────────────────────────────┘
       │ Response + Tool Result
       ▼
┌──────────────────────────────────────────────────────────────┐
│  5️⃣ TEXT-TO-SPEECH (Piper TTS)                              │
│     • Model: en_US-ryan-high.onnx                           │
│     • Engine: Piper with CUDA support                       │
│     • Queue: Async playback queue                           │
│     • Barge-In: Monitors for user speech                    │
│     • If speech detected → Stop TTS immediately             │
│     • Latency: <500ms synthesis                             │
└──────┬───────────────────────────────────────────────────────┘
       │ Audio output
       ▼
┌──────────────┐
│ 🔊 SPEAKER  │
└──────────────┘
       │
       │ (Barge-in monitoring)
       ▼
┌──────────────────────────────────────────────────────────────┐
│  6️⃣ BARGE-IN DETECTION                                      │
│     • Monitors audio stream during TTS playback             │
│     • Uses Silero VAD                                       │
│     • Threshold: speech_prob > 0.7                          │
│     • If user speaks → tts.stop_speaking()                  │
│     • Enables natural interruption                          │
└──────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1️⃣ Wake Word Detection

**Technology:** openWakeWord (ONNX on CPU)

**Files:**
- `wake_engine.py` - WakeWordEngine class
- `run_jarvis.py` - Integration point

**Key Methods:**
```python
self.wake_engine = WakeWordEngine(threshold=0.5)
await self.wake_engine.start_listening_async(on_wake_callback)
```

**Performance:**
- CPU Usage: 5-10% (idle listening)
- Latency: <500ms
- False Positives: Tunable via threshold

---

### 2️⃣ Speech-to-Text

**Technology:** faster-whisper + Silero VAD

**Files:**
- `stt_service.py` - STTService class
- `run_jarvis.py` - Integration

**Key Parameters:**
```python
STTService(
    model_size="distil-medium.en",
    device="cuda" or "cpu",
    compute_type="int8",
    min_silence_duration_ms=800,  # 47% faster
    vad_threshold=0.6
)
```

**Optimizations:**
- Auto-CUDA detection
- Aggressive VAD cutoff (800ms)
- Greedy decoding (beam_size=1)
- No timestamps, no context

**Performance:**
- GPU: 1-2s transcription
- CPU: 2-3s transcription
- Accuracy: 95%+ (English)

---

### 3️⃣ LLM Integration

**Technology:** Ollama / LM Studio (OpenAI-compatible API)

**Files:**
- `run_jarvis.py` - call_llm() function
- `system_prompts.py` - System prompts

**Configuration:**
```python
class LLMConfig:
    USE_LOCAL_LLM = True
    LOCAL_LLM_URL = "http://localhost:11434/v1/chat/completions"
    LOCAL_LLM_MODEL = "llama3.2"
```

**Response Format:**
```json
{
  "intent": "CHAT",
  "response": "The current time is 3:45 PM.",
  "action": null
}
```

**Fallback:**
- Mock mode with basic responses
- No internet required

---

### 4️⃣ MCP Tool Execution

**Technology:** MCP (Model Context Protocol) Integration Point

**Files:**
- `run_jarvis.py` - _execute_mcp_tools() method

**Flow:**
```
LLM Response
    ↓
{
  "intent": "FILE_SYSTEM",
  "action": {
    "type": "create_file",
    "parameters": {"path": "test.py"}
  }
}
    ↓
_execute_mcp_tools(action)
    ↓
MCP Server (your implementation)
    ↓
Tool Result
```

**Status:** Stub implemented, ready for integration

**Integration Example:**
```python
async with aiohttp.ClientSession() as session:
    async with session.post(MCP_URL, json=action) as resp:
        return await resp.json()
```

---

### 5️⃣ Text-to-Speech

**Technology:** Piper TTS (ONNX)

**Files:**
- `tts_service.py` - TTSService class
- `run_jarvis.py` - Integration

**Features:**
- Queue-based async playback
- Barge-in support (stop_speaking())
- CUDA acceleration
- Thread-safe

**Key Methods:**
```python
tts.speak_async(text)        # Non-blocking
tts.stop_speaking()          # Interrupt
tts.wait_until_done()        # Block until finished
```

**Performance:**
- Synthesis: <500ms
- Quality: High (neural TTS)
- Voice: en_US-ryan-high

---

### 6️⃣ Barge-In System

**Technology:** Real-time audio monitoring + Silero VAD

**Files:**
- `run_jarvis.py` - _speak_with_barge_in() method

**Process:**
```python
1. Start TTS (non-blocking)
2. Open microphone stream
3. While TTS is playing:
   - Read audio chunk (512 samples)
   - Run VAD detection
   - If speech_prob > 0.7:
     - Stop TTS immediately
     - Break loop
4. Close microphone stream
```

**Tuning:**
- Threshold: 0.7 (higher = harder to trigger)
- Chunk size: 512 samples (low latency)
- Monitor: Only during long responses

---

## Data Flow Example

### User: "Hey Jarvis, what time is it?"

```
Step 1: Wake Word Detection
   Input:  Audio stream
   Output: Wake event triggered
   Time:   <500ms

Step 2: State Transition
   From:   IDLE
   To:     ACTIVE
   Action: Play "Yes?" acknowledgment

Step 3: Listen for Command
   From:   ACTIVE
   To:     LISTENING
   Input:  Audio stream
   VAD:    Detect speech start/end
   Output: Raw audio buffer
   Time:   ~3s (user speaks)

Step 4: Transcription
   From:   LISTENING
   To:     PROCESSING
   Input:  Audio buffer
   Model:  faster-whisper (distil-medium.en)
   Output: "what time is it?"
   Time:   1-2s (GPU) / 2-3s (CPU)

Step 5: LLM Processing
   Input:  "what time is it?"
   System: get_router_prompt()
   Model:  llama3.2 (Ollama)
   Output: {
     "intent": "CHAT",
     "response": "The current time is 3:45 PM.",
     "action": null
   }
   Time:   <1s (local)

Step 6: MCP Tool Execution
   Input:  null (no action)
   Output: null
   Time:   0s (skipped)

Step 7: Text-to-Speech
   From:   PROCESSING
   To:     SPEAKING
   Input:  "The current time is 3:45 PM."
   Model:  Piper TTS
   Output: Audio stream
   Time:   <500ms synthesis + 2s playback
   Monitor: Barge-in active

Step 8: Return to Active
   From:   SPEAKING
   To:     ACTIVE
   Timer:  5-second window starts
   Ready:  For follow-up command

TOTAL LATENCY: ~3-5s (Wake → Response)
```

---

## State Machine Details

### IDLE State
- **Activity:** Wake word listening only
- **CPU Usage:** Low (5-10%)
- **Transition:** Wake word detected → ACTIVE

### ACTIVE State
- **Duration:** 5 seconds (configurable)
- **Activity:** Ready for command
- **Transition:** 
  - User speaks → LISTENING
  - Timeout (5s) → IDLE

### LISTENING State
- **Activity:** Recording user speech
- **VAD:** Monitors speech start/end
- **Cutoff:** 800ms silence
- **Transition:** Speech ended → PROCESSING

### PROCESSING State
- **Activity:** STT + LLM + MCP Tools
- **Output:** Structured response
- **Transition:** Complete → SPEAKING

### SPEAKING State
- **Activity:** TTS playback
- **Monitoring:** Barge-in detection
- **Interrupt:** User speech → Stop TTS
- **Transition:** Complete → ACTIVE

---

## Performance Optimization Points

### 🚀 Fast Path (Optimized)
```
Wake Word (500ms)
    ↓
STT (1-2s GPU)
    ↓
LLM (1s local)
    ↓
TTS (500ms)
    ↓
TOTAL: ~3s
```

### 🐌 Slow Path (Worst Case)
```
Wake Word (500ms)
    ↓
STT (3s CPU)
    ↓
LLM (2s remote)
    ↓
TTS (500ms)
    ↓
TOTAL: ~6s
```

### ⚡ Optimization Targets
- STT: Use GPU, tune VAD aggressively
- LLM: Use local Ollama, smaller models
- TTS: Pre-warm model, use queue
- Network: Minimize API calls

---

## Error Handling

### Graceful Degradation

```
Wake Word Failed
    ↓
Manual fallback (Enter key simulation)

LLM Unavailable
    ↓
Mock mode (basic responses)

STT Timeout
    ↓
Prompt user to try again

TTS Failed
    ↓
Text-only mode (print response)

GPU Unavailable
    ↓
Auto-fallback to CPU
```

---

## Configuration Hierarchy

```
User Configuration
    ├── wake_word_threshold (0.5)
    ├── active_window_seconds (5.0)
    ├── llm_model ("llama3.2")
    ├── llm_url (localhost:11434)
    ├── stt_device ("cuda" or "cpu")
    ├── min_silence_duration_ms (800)
    ├── vad_threshold (0.6)
    ├── barge_in_threshold (0.7)
    └── tts_model_path ("models/en_US-ryan-high.onnx")
```

---

## Thread Safety

### Thread Model

```
Main Thread (asyncio)
    ├── Wake word detection (async)
    ├── STT processing (async executor)
    ├── LLM calls (async HTTP)
    ├── Barge-in monitoring (async)
    └── TTS playback (worker thread)
            └── Audio output (thread-safe queue)
```

### Synchronization

- **Queue:** TTS uses thread-safe queue
- **Events:** Wake word uses asyncio.Event
- **Locks:** Not needed (single producer)

---

**This architecture provides a robust, responsive, and scalable voice assistant system! 🏗️**
