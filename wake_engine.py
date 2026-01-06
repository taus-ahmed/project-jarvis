"""
Wake Word Detection Engine using openWakeWord.
Listens for 'Hey Mycroft' trigger phrase on CPU.
Downloads models on first use if needed.
"""

import asyncio
import numpy as np
import pyaudio
from openwakeword.model import Model
from openwakeword import utils
from typing import Callable, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WakeWordEngine:
    """
    Detects 'Hey Mycroft' wake word using openWakeWord on CPU.
    Uses built-in models that are pre-packaged with openwakeword.
    Streams audio and triggers callback when wake word is detected.
    """
    
    def __init__(
        self,
        model_name: str = "hey_mycroft",
        threshold: float = 0.5,
        chunk_size: int = 1280,  # 80ms at 16kHz
        sample_rate: int = 16000,
        channels: int = 1
    ):
        """
        Initialize wake word engine with built-in models.
        
        Args:
            model_name: Built-in model name ('hey_mycroft', 'alexa', etc.)
                       If None, uses all available built-in models
            threshold: Detection threshold (0.0 to 1.0)
            chunk_size: Audio chunk size in samples
            sample_rate: Audio sample rate in Hz
            channels: Number of audio channels
        """
        self.threshold = threshold
        self.chunk_size = chunk_size
        self.sample_rate = sample_rate
        self.channels = channels
        self.is_running = False
        self.audio = None
        self.stream = None
        
        # Initialize openWakeWord model with built-in models
        logger.info("Loading openWakeWord with built-in models...")
        
        try:
            # Load using built-in model (pre-packaged, no downloads needed)
            if model_name:
                logger.info(f"Loading model: {model_name}")
                self.model = Model(
                    wakeword_models=[model_name],
                    inference_framework="onnx"
                )
                logger.info(f"✅ Loaded wake word model: {model_name}")
            else:
                # Load all available built-in models
                self.model = Model(inference_framework="onnx")
                logger.info(f"✅ Loaded all available models")
            
            # Log available models
            available = list(self.model.models.keys())
            logger.info(f"Available wake words: {', '.join(available)}")
            
            if not available:
                raise RuntimeError("No wake word models loaded")
            
        except Exception as e:
            logger.error(f"Failed to load wake word models: {e}")
            logger.error("Make sure openwakeword is properly installed:")
            logger.error("  pip install openwakeword")
            raise
    
    def start_listening(self, on_wake_callback: Callable[[], None]):
        """
        Start listening for wake word in blocking mode.
        
        Args:
            on_wake_callback: Function to call when wake word is detected
        """
        if self.is_running:
            logger.warning("Wake word engine is already running")
            return
            
        self.is_running = True
        
        # Initialize PyAudio
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size
        )
        
        # Get the wake word name to log
        wake_words = list(self.model.models.keys())
        wake_word_display = wake_words[0] if wake_words else "wake word"
        
        logger.info(f"🎧 Listening for '{wake_word_display}'...")
        
        try:
            while self.is_running:
                # Read audio chunk
                audio_data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                
                # Get predictions from model
                prediction = self.model.predict(audio_array)
                
                # Check if wake word detected
                for wake_word, score in prediction.items():
                    if score >= self.threshold:
                        logger.info(f"🎙️ Wake word detected! (confidence: {score:.2f})")
                        on_wake_callback()
                        
        except KeyboardInterrupt:
            logger.info("Wake word detection interrupted")
        finally:
            self.stop_listening()
    
    async def start_listening_async(self, on_wake_callback: Callable[[], None]):
        """
        Start listening for wake word asynchronously.
        
        Args:
            on_wake_callback: Async or sync function to call when wake word is detected
        """
        if self.is_running:
            logger.warning("Wake word engine is already running")
            return
            
        self.is_running = True
        
        # Initialize PyAudio
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size
        )
        
        # Get the wake word name to log
        wake_words = list(self.model.models.keys())
        wake_word_display = wake_words[0] if wake_words else "wake word"
        
        logger.info(f"🎧 Listening for '{wake_word_display}'...")
        
        try:
            while self.is_running:
                # Read audio chunk in executor to avoid blocking
                loop = asyncio.get_event_loop()
                
                # Define read function to avoid positional argument issues
                def read_audio():
                    return self.stream.read(self.chunk_size, exception_on_overflow=False)
                
                audio_data = await loop.run_in_executor(None, read_audio)
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                
                # Run model prediction in executor (CPU intensive)
                prediction = await loop.run_in_executor(
                    None,
                    self.model.predict,
                    audio_array
                )
                
                # Check if wake word detected
                for wake_word, score in prediction.items():
                    if score >= self.threshold:
                        logger.info(f"🎙️ Wake word detected! (confidence: {score:.2f})")
                        if asyncio.iscoroutinefunction(on_wake_callback):
                            await on_wake_callback()
                        else:
                            await loop.run_in_executor(None, on_wake_callback)
                        return  # Exit after detection
                        
        except asyncio.CancelledError:
            logger.info("Wake word detection cancelled")
        finally:
            self.stop_listening()
    
    def stop_listening(self):
        """Stop listening for wake word and clean up resources."""
        self.is_running = False
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
            
        if self.audio:
            self.audio.terminate()
            self.audio = None
            
        logger.info("Wake word engine stopped")


async def main():
    """Example usage of WakeWordEngine."""
    
    async def on_wake():
        print("\n🎙️ Jarvis activated! Listening for command...\n")
    
    engine = WakeWordEngine(threshold=0.5)
    
    try:
        await engine.start_listening_async(on_wake)
    except KeyboardInterrupt:
        print("\nShutting down...")


if __name__ == "__main__":
    asyncio.run(main())
        
    def start_listening(self, on_wake_callback: Callable[[], None]):
        """
        Start listening for wake word in blocking mode.
        
        Args:
            on_wake_callback: Function to call when wake word is detected
        """
        if self.is_running:
            logger.warning("Wake word engine is already running")
            return
            
        self.is_running = True
        
        # Initialize PyAudio
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size
        )
        
        logger.info("Listening for 'Hey Jarvis'...")
        
        try:
            while self.is_running:
                # Read audio chunk
                audio_data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                
                # Get predictions from model
                prediction = self.model.predict(audio_array)
                
                # Check if wake word detected
                for wake_word, score in prediction.items():
                    if score >= self.threshold:
                        logger.info(f"Wake word detected! (confidence: {score:.2f})")
                        on_wake_callback()
                        
        except KeyboardInterrupt:
            logger.info("Wake word detection interrupted")
        finally:
            self.stop_listening()
    
    async def start_listening_async(self, on_wake_callback: Callable[[], None]):
        """
        Start listening for wake word asynchronously.
        
        Args:
            on_wake_callback: Async function to call when wake word is detected
        """
        if self.is_running:
            logger.warning("Wake word engine is already running")
            return
            
        self.is_running = True
        
        # Initialize PyAudio
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size
        )
        
        logger.info("Listening for 'Hey Jarvis'...")
        
        try:
            while self.is_running:
                # Read audio chunk in executor to avoid blocking
                loop = asyncio.get_event_loop()
                audio_data = await loop.run_in_executor(
                    None,
                    self.stream.read,
                    self.chunk_size,
                    False  # exception_on_overflow
                )
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                
                # Run model prediction in executor (CPU intensive)
                prediction = await loop.run_in_executor(
                    None,
                    self.model.predict,
                    audio_array
                )
                
                # Check if wake word detected
                for wake_word, score in prediction.items():
                    if score >= self.threshold:
                        logger.info(f"Wake word detected! (confidence: {score:.2f})")
                        if asyncio.iscoroutinefunction(on_wake_callback):
                            await on_wake_callback()
                        else:
                            on_wake_callback()
                        
        except asyncio.CancelledError:
            logger.info("Wake word detection cancelled")
        finally:
            self.stop_listening()
    
    def stop_listening(self):
        """Stop listening for wake word and clean up resources."""
        self.is_running = False
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
            
        if self.audio:
            self.audio.terminate()
            self.audio = None
            
        logger.info("Wake word engine stopped")


async def main():
    """Example usage of WakeWordEngine."""
    
    async def on_wake():
        print("\n🎙️ Jarvis activated! Listening for command...\n")
    
    engine = WakeWordEngine(threshold=0.5)
    
    try:
        await engine.start_listening_async(on_wake)
    except KeyboardInterrupt:
        print("\nShutting down...")


if __name__ == "__main__":
    asyncio.run(main())
