"""
Text-to-Speech Service using Piper TTS with GPU acceleration.
Production-grade implementation with queue-based playback and barge-in support.
"""

import asyncio
import numpy as np
import pyaudio
import threading
import queue
import time
from typing import Optional, Callable
import logging
import subprocess
import os
import json
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TTSService:
    """
    Production-grade Text-to-Speech service using Piper TTS.
    Features:
    - GPU acceleration via CUDA (onnxruntime-gpu)
    - Queue-based async playback
    - Barge-in support (stop speaking on demand)
    - Thread-safe operation
    """
    
    def __init__(
        self,
        model_path: str = "models/en_US-ryan-high.onnx",
        config_path: Optional[str] = None,
        use_cuda: bool = True,
        speaker_id: Optional[int] = None,
        length_scale: float = 1.0,
        noise_scale: float = 0.667,
        noise_w: float = 0.8,
        sample_rate: int = 22050,
        piper_executable: Optional[str] = None
    ):
        """
        Initialize TTS service with GPU acceleration and queue-based playback.
        
        Args:
            model_path: Path to Piper ONNX model file
            config_path: Path to model config JSON
            use_cuda: Enable CUDA acceleration
            piper_executable: Path to piper executable (None = auto-detect)
            speaker_id: Speaker ID for multi-speaker models
            length_scale: Speed factor (< 1.0 = faster, > 1.0 = slower)
            noise_scale: Variation in speech
            noise_w: Variation in phoneme duration
            sample_rate: Output sample rate
        """
        # Initialize control structures first (for safe cleanup)
        self.speech_queue = queue.Queue()
        self.is_speaking = False
        self.should_stop = threading.Event()
        self.worker_running = False
        self.audio = None
        self.stream = None
        self.worker_thread = None
        
        # Now set configuration
        self.model_path = Path(model_path)
        self.use_cuda = use_cuda
        self.speaker_id = speaker_id
        self.length_scale = length_scale
        self.noise_scale = noise_scale
        self.noise_w = noise_w
        self.sample_rate = sample_rate
        
        # Auto-detect Piper executable
        if piper_executable:
            self.piper_exe = piper_executable
        else:
            # Check local piper directory (with DLLs in subdirectory)
            local_piper_with_dlls = Path("piper/piper/piper.exe")
            local_piper_root = Path("piper/piper.exe")
            
            if local_piper_with_dlls.exists():
                self.piper_exe = str(local_piper_with_dlls.absolute())
            elif local_piper_root.exists():
                self.piper_exe = str(local_piper_root.absolute())
            else:
                self.piper_exe = "piper"  # Assume in PATH
        
        # Auto-detect config path
        if config_path is None:
            config_path = str(self.model_path) + ".json"
        self.config_path = Path(config_path)
        
        # Validate installation
        self._check_piper_installation()
        self._load_config()
        
        # Delay worker thread start to avoid PyAudio conflicts with wake word engine
        # Worker will be started lazily on first use
        self.worker_thread = None
        self.worker_running = False
        
        logger.info(f"✅ TTS Service initialized with {self.model_path.name}")
        if self.use_cuda:
            logger.info("🎮 GPU acceleration enabled (CUDA)")
    
    def _ensure_worker_started(self):
        """Start worker thread if not already running (lazy initialization)."""
        if not self.worker_running and self.worker_thread is None:
            logger.info("🔊 Starting TTS playback worker...")
            self.worker_thread = threading.Thread(target=self._playback_worker, daemon=True)
            self.worker_thread.start()
            self.worker_running = True
            logger.info("🔊 TTS playback worker started")
    
    def _check_piper_installation(self):
        """Check if Piper is installed and accessible."""
        try:
            result = subprocess.run(
                [self.piper_exe, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            version = result.stdout.strip() or result.stderr.strip()
            logger.info(f"Piper found: {version or 'OK'}")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            raise RuntimeError(
                "Piper executable not found. Install from: "
                "https://github.com/rhasspy/piper/releases"
            )
    
    def _load_config(self):
        """Load and validate model configuration."""
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found: {self.model_path}")
        
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            logger.info(f"Loaded config: {self.config_path.name}")
        else:
            logger.warning(f"Config not found: {self.config_path}")
            self.config = {}
    
    def synthesize(self, text: str) -> np.ndarray:
        """
        Synthesize speech from text (synchronous).
        
        Args:
            text: Text to convert to speech
            
        Returns:
            Audio samples as numpy array (int16)
        """
        if not text.strip():
            return np.array([], dtype=np.int16)
        
        # Build Piper command with CUDA support
        cmd = [
            self.piper_exe,
            "--model", str(self.model_path),
            "--config", str(self.config_path),
            "--output_raw"
        ]
        
        # Add CUDA flag if available (check Piper version for support)
        if self.use_cuda:
            cmd.extend(["--cuda"])  # If your Piper build supports it
        
        # Add optional parameters
        if self.speaker_id is not None:
            cmd.extend(["--speaker", str(self.speaker_id)])
        if self.length_scale != 1.0:
            cmd.extend(["--length_scale", str(self.length_scale)])
        if self.noise_scale != 0.667:
            cmd.extend(["--noise_scale", str(self.noise_scale)])
        if self.noise_w != 0.8:
            cmd.extend(["--noise_w", str(self.noise_w)])
        
        try:
            start_time = time.time()
            
            # Run Piper and capture raw PCM audio
            result = subprocess.run(
                cmd,
                input=text.encode('utf-8'),
                capture_output=True,
                text=False,
                timeout=10
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.decode('utf-8', errors='ignore')
                logger.error(f"Piper error: {error_msg}")
                return np.array([], dtype=np.int16)
            
            # Convert raw bytes to numpy array
            audio_data = np.frombuffer(result.stdout, dtype=np.int16)
            
            elapsed = time.time() - start_time
            duration = len(audio_data) / self.sample_rate
            logger.info(f"Synthesized {duration:.2f}s audio in {elapsed:.2f}s")
            
            return audio_data
            
        except subprocess.TimeoutExpired:
            logger.error("Piper synthesis timed out")
            return np.array([], dtype=np.int16)
        except Exception as e:
            logger.error(f"Synthesis error: {e}")
            return np.array([], dtype=np.int16)
    
    def _playback_worker(self):
        """Background worker thread for queue-based audio playback."""

        
        # Initialize PyAudio once
        self.audio = pyaudio.PyAudio()
        
        while self.worker_running:
            try:
                # Get next item from queue (blocking with timeout)
                audio_data = self.speech_queue.get(timeout=0.5)
                
                if audio_data is None:  # Poison pill for shutdown
                    break
                
                # Play the audio
                self._play_audio_blocking(audio_data)
                
                self.speech_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Playback worker error: {e}")
        
        # Cleanup
        if self.audio:
            self.audio.terminate()
        
        logger.info("🔊 TTS playback worker stopped")
    
    def _play_audio_blocking(self, audio_data: np.ndarray):
        """
        Play audio data with barge-in support (can be interrupted).
        
        Args:
            audio_data: Audio samples as numpy array (int16)
        """
        if len(audio_data) == 0:
            return
        
        try:
            self.is_speaking = True
            self.should_stop.clear()
            
            # Open stream
            stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                output=True,
                frames_per_buffer=1024
            )
            
            # Stream audio in chunks for interruptibility
            chunk_size = 1024
            audio_bytes = audio_data.tobytes()
            
            for i in range(0, len(audio_bytes), chunk_size * 2):  # *2 for int16
                if self.should_stop.is_set():
                    logger.info("🛑 TTS interrupted (barge-in)")
                    break
                
                chunk = audio_bytes[i:i + chunk_size * 2]
                stream.write(chunk)
            
            # Cleanup
            stream.stop_stream()
            stream.close()
            
        except Exception as e:
            logger.error(f"Audio playback error: {e}")
        finally:
            self.is_speaking = False
    
    def speak_async(self, text: str):
        """
        Add text to speech queue for async playback.
        Non-blocking - returns immediately.
        
        Args:
            text: Text to speak
        """
        if not text.strip():
            return
        
        # Ensure worker is started (lazy init to avoid PyAudio conflicts)
        self._ensure_worker_started()
        
        # Synthesize audio
        audio_data = self.synthesize(text)
        
        if len(audio_data) > 0:
            # Add to queue
            self.speech_queue.put(audio_data)
            logger.info(f"📢 Queued speech: \"{text[:50]}...\"")
    
    async def speak(self, text: str):
        """
        Speak text asynchronously (awaitable).
        
        Args:
            text: Text to speak
        """
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.speak_async, text)
    
    def stop_speaking(self):
        """
        Immediately stop current speech (barge-in).
        Clears queue and stops playback.
        """
        logger.info("🛑 Stopping speech (barge-in triggered)")
        
        # Signal playback to stop
        self.should_stop.set()
        
        # Clear queue
        while not self.speech_queue.empty():
            try:
                self.speech_queue.get_nowait()
                self.speech_queue.task_done()
            except queue.Empty:
                break
        
        # Wait briefly for playback to stop
        timeout = 0.5
        start = time.time()
        while self.is_speaking and (time.time() - start) < timeout:
            time.sleep(0.01)
    
    def wait_until_done(self, timeout: Optional[float] = None):
        """
        Wait until all queued speech is finished.
        
        Args:
            timeout: Max time to wait in seconds
        """
        try:
            self.speech_queue.join()
        except KeyboardInterrupt:
            self.stop_speaking()
    
    def shutdown(self):
        """Gracefully shutdown the TTS service."""
        if not hasattr(self, 'speech_queue'):
            return  # Not fully initialized
            
        logger.info("Shutting down TTS service...")
        
        self.worker_running = False
        
        try:
            self.speech_queue.put(None)  # Poison pill
        except:
            pass
        
        if hasattr(self, 'worker_thread') and self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=2.0)
    
    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.shutdown()
        except:
            pass


async def main():
    """Example usage of enhanced TTSService."""
    
    # Initialize Piper TTS with GPU
    tts = TTSService(
        model_path="models/en_US-ryan-high.onnx",
        use_cuda=True,
        length_scale=1.0  # Normal speed
    )
    
    print("🎤 Testing TTS with queue and barge-in...\n")
    
    # Queue multiple messages
    tts.speak_async("Hello! I am Jarvis, your desktop assistant.")
    tts.speak_async("I can help you with various tasks.")
    
    # Wait a bit
    await asyncio.sleep(2)
    
    # Test barge-in
    print("⚠️  Triggering barge-in (stop speaking)...")
    tts.stop_speaking()
    
    # New message after interruption
    tts.speak_async("I was interrupted, but now I'm back!")
    
    # Wait for completion
    tts.wait_until_done()
    
    print("\n✅ Test complete!")
    tts.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
