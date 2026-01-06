"""
Speech-to-Text Service using faster-whisper with GPU acceleration.
Includes Silero VAD for automatic speech detection.
"""

import asyncio
import numpy as np
import pyaudio
import torch
from faster_whisper import WhisperModel
from typing import Optional, List
import logging
from collections import deque
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class STTService:
    """
    Speech-to-Text service using faster-whisper on GPU with Silero VAD.
    Optimized for <1s latency using distil-medium model with int8 quantization.
    """
    
    def __init__(
        self,
        model_size: str = "distil-medium.en",
        device: str = "cuda",
        compute_type: str = "int8",
        vad_threshold: float = 0.6,  # Increased from 0.5 for better sensitivity
        sample_rate: int = 16000,
        chunk_duration_ms: int = 30,
        padding_duration_ms: int = 300,
        min_speech_duration_ms: int = 200,  # Reduced from 250ms for faster trigger
        min_silence_duration_ms: int = 800  # Reduced from 1500ms for faster cutoff
    ):
        """
        Initialize STT service with faster-whisper and Silero VAD.
        
        Args:
            model_size: Whisper model size (distil-medium.en for speed)
            device: Device to run on ("cuda" or "cpu") - auto-detects GPU
            compute_type: Computation precision ("int8" for speed, "float16" for accuracy)
            vad_threshold: VAD sensitivity (0.0 to 1.0, higher = more selective)
            sample_rate: Audio sample rate in Hz
            chunk_duration_ms: Audio chunk duration in milliseconds
            padding_duration_ms: Audio padding for context
            min_speech_duration_ms: Minimum speech duration to trigger (lower = faster)
            min_silence_duration_ms: Silence duration to end speech (lower = faster cutoff)
        """
        # Auto-detect CUDA availability
        if device == "cuda" and not torch.cuda.is_available():
            logger.warning("⚠️ CUDA requested but not available, falling back to CPU")
            device = "cpu"
            compute_type = "int8"  # CPU uses int8
        
        if device == "cuda":
            logger.info(f"🎮 Using GPU: {torch.cuda.get_device_name(0)}")
        else:
            logger.info("💻 Using CPU for STT")
        self.device = device
        self.sample_rate = sample_rate
        self.chunk_duration_ms = chunk_duration_ms
        self.padding_duration_ms = padding_duration_ms
        self.min_speech_duration_ms = min_speech_duration_ms
        self.min_silence_duration_ms = min_silence_duration_ms
        self.vad_threshold = vad_threshold
        
        # Calculate chunk size (minimum 512 samples for Silero VAD)
        self.chunk_size = max(512, int(sample_rate * chunk_duration_ms / 1000))
        self.padding_chunks = int(padding_duration_ms / chunk_duration_ms)
        
        # Load faster-whisper model
        logger.info(f"Loading faster-whisper {model_size} on {device} with {compute_type}...")
        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
            download_root=None,
            local_files_only=False
        )
        logger.info("Whisper model loaded successfully")
        
        # Load Silero VAD
        logger.info("Loading Silero VAD...")
        self.vad_model, utils = torch.hub.load(
            repo_or_dir='snakers4/silero-vad',
            model='silero_vad',
            force_reload=False
        )
        self.vad_model.to("cpu")  # Keep VAD on CPU to save GPU
        self.get_speech_timestamps = utils[0]
        logger.info("VAD model loaded successfully")
        
        # Audio buffer
        self.audio_buffer = deque(maxlen=self.padding_chunks * 2)
        self.is_listening = False
        
    def transcribe_audio(self, audio_data: np.ndarray, language: str = "en") -> str:
        """
        Transcribe audio data synchronously with optimized settings.
        
        Args:
            audio_data: Audio samples as numpy array (float32, normalized to [-1, 1])
            language: Language code for transcription
            
        Returns:
            Transcribed text
        """
        start_time = time.time()
        
        segments, info = self.model.transcribe(
            audio_data,
            language=language,
            beam_size=1,  # Faster inference (use 5 for better accuracy)
            best_of=1,    # No sampling alternatives (faster)
            vad_filter=False,  # We handle VAD separately
            without_timestamps=True,  # Skip timestamps for speed
            condition_on_previous_text=False,  # Disable context (faster)
            temperature=0.0,  # Greedy decoding (deterministic, faster)
            compression_ratio_threshold=2.4,  # Default
            log_prob_threshold=-1.0,  # Default
            no_speech_threshold=0.6,  # Filter silence
            initial_prompt=None  # No prompt context
        )
        
        # Collect all segments
        transcription = " ".join([segment.text for segment in segments])
        
        elapsed = time.time() - start_time
        logger.info(f"⏱️ Transcription: {elapsed:.2f}s | Text: {transcription}")
        
        return transcription.strip()
    
    async def transcribe_audio_async(self, audio_data: np.ndarray, language: str = "en") -> str:
        """
        Transcribe audio data asynchronously.
        
        Args:
            audio_data: Audio samples as numpy array (float32, normalized to [-1, 1])
            language: Language code for transcription
            
        Returns:
            Transcribed text
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.transcribe_audio,
            audio_data,
            language
        )
    
    def detect_speech(self, audio_chunk: np.ndarray) -> float:
        """
        Detect speech in audio chunk using Silero VAD.
        
        Args:
            audio_chunk: Audio samples as numpy array (int16 or float32)
            
        Returns:
            Speech probability (0.0 to 1.0)
        """
        # Silero VAD requires minimum audio length
        # Skip detection if chunk is too small
        if len(audio_chunk) < 512:
            return 0.0
        
        # Convert to tensor and normalize if needed
        if audio_chunk.dtype == np.int16:
            audio_tensor = torch.from_numpy(audio_chunk.copy()).float() / 32768.0
        else:
            audio_tensor = torch.from_numpy(audio_chunk.copy()).float()
            
        # Get speech probability
        try:
            speech_prob = self.vad_model(audio_tensor, self.sample_rate).item()
            return speech_prob
        except Exception as e:
            # If VAD fails, return neutral probability
            logger.debug(f"VAD detection failed: {e}")
            return 0.5
    
    async def transcribe_stream(
        self,
        audio_stream: Optional[pyaudio.Stream] = None,
        duration_seconds: Optional[float] = None,
        language: str = "en"
    ) -> str:
        """
        Transcribe audio from stream with automatic VAD-based cutoff.
        
        Args:
            audio_stream: PyAudio stream. If None, creates a new stream.
            duration_seconds: Max recording duration. If None, uses VAD to detect end.
            language: Language code for transcription
            
        Returns:
            Transcribed text
        """
        own_stream = False
        audio = None
        
        try:
            # Create stream if not provided
            if audio_stream is None:
                audio = pyaudio.PyAudio()
                audio_stream = audio.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=self.sample_rate,
                    input=True,
                    frames_per_buffer=self.chunk_size
                )
                own_stream = True
            
            logger.info("Recording audio...")
            
            # Recording state
            audio_chunks = []
            speech_started = False
            silence_start = None
            start_time = time.time()
            
            min_speech_chunks = int(self.min_speech_duration_ms / self.chunk_duration_ms)
            min_silence_chunks = int(self.min_silence_duration_ms / self.chunk_duration_ms)
            
            while True:
                # Check max duration
                if duration_seconds and (time.time() - start_time) > duration_seconds:
                    logger.info("Max duration reached")
                    break
                
                # Read audio chunk
                loop = asyncio.get_event_loop()
                audio_data = await loop.run_in_executor(
                    None,
                    audio_stream.read,
                    self.chunk_size,
                    False
                )
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                audio_chunks.append(audio_array)
                
                # Detect speech
                speech_prob = await loop.run_in_executor(
                    None,
                    self.detect_speech,
                    audio_array
                )
                
                # Speech detection logic
                if speech_prob > self.vad_threshold:
                    if not speech_started:
                        logger.info("Speech detected, recording...")
                        speech_started = True
                    silence_start = None
                else:
                    if speech_started:
                        if silence_start is None:
                            silence_start = len(audio_chunks)
                        
                        # Check if enough silence to stop
                        silence_chunks = len(audio_chunks) - silence_start
                        if silence_chunks >= min_silence_chunks:
                            logger.info("Speech ended, processing...")
                            break
                
                # Prevent infinite recording if no speech detected
                if not speech_started and len(audio_chunks) > 100:  # ~3 seconds
                    logger.warning("No speech detected in timeout period")
                    return ""
            
            # Check if we have enough audio
            if len(audio_chunks) < min_speech_chunks:
                logger.warning("Insufficient audio captured")
                return ""
            
            # Concatenate audio chunks
            audio_data = np.concatenate(audio_chunks)
            
            # Convert to float32 and normalize
            audio_float = audio_data.astype(np.float32) / 32768.0
            
            # Transcribe
            transcription = await self.transcribe_audio_async(audio_float, language)
            
            return transcription
            
        finally:
            # Clean up if we created our own stream
            if own_stream and audio_stream:
                audio_stream.stop_stream()
                audio_stream.close()
            if audio:
                audio.terminate()
    
    async def transcribe_from_buffer(
        self,
        audio_buffer: List[np.ndarray],
        language: str = "en"
    ) -> str:
        """
        Transcribe audio from a pre-recorded buffer.
        
        Args:
            audio_buffer: List of audio chunks (int16 numpy arrays)
            language: Language code for transcription
            
        Returns:
            Transcribed text
        """
        if not audio_buffer:
            return ""
        
        # Concatenate buffer
        audio_data = np.concatenate(audio_buffer)
        
        # Convert to float32 and normalize
        audio_float = audio_data.astype(np.float32) / 32768.0
        
        # Transcribe
        transcription = await self.transcribe_audio_async(audio_float, language)
        
        return transcription


async def main():
    """Example usage of STTService."""
    
    # Initialize service
    stt = STTService(
        model_size="distil-medium.en",
        device="cuda",
        compute_type="int8"
    )
    
    print("Say something after the beep...\n")
    
    # Record and transcribe
    transcription = await stt.transcribe_stream(duration_seconds=10)
    
    print(f"\n📝 Transcription: {transcription}\n")


if __name__ == "__main__":
    asyncio.run(main())
