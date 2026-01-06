# Wake Word Configuration Guide

## Available Wake Words

OpenWakeWord comes with several pre-trained models. Since a specific "Hey Jarvis" model isn't included by default, you can use one of these options:

### Option 1: Use Built-in Models (Easiest)

The system now loads ALL available default models. Common ones include:
- **"hey_mycroft"** - Say "Hey Mycroft"
- **"alexa"** - Say "Alexa"
- **"hey_rhasspy"** - Say "Hey Rhasspy"

Run the system and it will show you which models are available:
```powershell
python main.py
# Look for: "Available wake words: ['hey_mycroft', 'alexa', ...]"
```

### Option 2: Download More Models

OpenWakeWord has additional models you can download:

```python
from openwakeword import Model

# This downloads all available pre-trained models
model = Model()

# List what's available
print(model.models.keys())
```

### Option 3: Train Custom "Hey Jarvis" Model

To create a true "Hey Jarvis" wake word:

1. **Collect Training Data**: Record yourself saying "Hey Jarvis" 50-100 times
2. **Use OpenWakeWord Training**: Follow [training guide](https://github.com/dscripka/openWakeWord#training-new-models)
3. **Export Model**: Get `.onnx` and `.tflite` files
4. **Update Code**:
   ```python
   wake_engine = WakeWordEngine(
       model_path="path/to/hey_jarvis_custom.onnx",
       threshold=0.5
   )
   ```

### Option 4: Use Pre-trained Community Models

Check [OpenWakeWord Model Hub](https://github.com/dscripka/openWakeWord#pre-trained-models) for community-trained models.

## Current Setup

The code is now configured to:
1. Load ALL default models automatically
2. Display available wake words on startup
3. Listen for ANY detected wake word

## Testing

```powershell
# Test wake word detection
python wake_engine.py

# When prompted, say one of the available wake words
# e.g., "Hey Mycroft" or "Alexa"
```

## Quick Fix for Right Now

The easiest immediate solution is to use **"Hey Mycroft"** instead of "Hey Jarvis" since it's a built-in model. The system will work identically, just with a different trigger phrase.

Later, you can train a custom "Hey Jarvis" model or substitute Jarvis's personality/responses while keeping the "Hey Mycroft" trigger.
