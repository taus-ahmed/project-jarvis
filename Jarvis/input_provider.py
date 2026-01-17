# Jarvis/input_provider.py

import re
import tempfile
import numpy as np
import sounddevice as sd
import whisper
from scipy.io.wavfile import write as write_wav


def normalize_voice_text(text: str) -> str:
    """
    Normalize voice transcription for command parsing.
    """
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)   # remove punctuation
    text = re.sub(r"\s+", " ", text)     # normalize spaces
    return text


class InputProvider:
    def get_input(self) -> str:
        raise NotImplementedError


class TextInputProvider(InputProvider):
    def get_input(self) -> str:
        return input("You > ").strip()


class VoiceInputProvider(InputProvider):
    """
    Push-to-talk voice input using Whisper (CPU-safe).
    """

    def __init__(self, duration: int = 4, sample_rate: int = 16000):
        self.duration = duration
        self.sample_rate = sample_rate
        print("🎤 Loading Whisper model (first time may take a bit)...")
        self.model = whisper.load_model("tiny")  # CPU-safe

    def get_input(self) -> str:
        input("🎤 Press Enter to speak...")

        print("🎤 Listening...")
        audio = sd.rec(
            int(self.duration * self.sample_rate),
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
        )
        sd.wait()

        audio = np.squeeze(audio)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            write_wav(tmp.name, self.sample_rate, audio)
            result = self.model.transcribe(tmp.name)

        raw = result.get("text", "").strip()

        if len(raw) < 3:
            print("🤔 Low confidence speech, ignoring.")
            return ""

        text = normalize_voice_text(raw)
        print(f"🗣️  You said: {text}")
        return text



