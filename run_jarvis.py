"""
🤖 JARVIS - Your AI Voice Assistant
====================================

Single entry point to start Jarvis with:
- Wake word detection ("Hey Jarvis" or custom)
- Speech-to-text with VAD
- LLM integration for intelligent responses
- Text-to-speech playback

Just run: python run_jarvis.py
"""

import asyncio
import logging
import time
import json
from typing import Optional, Dict, Any
from enum import Enum
from datetime import datetime
import os
import torch
import numpy as np
import sys

# Force UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from stt_service import STTService
from tts_service import TTSService
from system_prompts import get_router_prompt

# Wake word engine for autonomous activation
from wake_engine import WakeWordEngine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# LLM INTEGRATION - CONFIGURE YOUR API HERE
# ============================================================================

class LLMConfig:
    """Configure your LLM API here."""
    
    # Option 1: OpenAI API
    USE_OPENAI = False
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = "gpt-4"
    OPENAI_BASE_URL = "https://api.openai.com/v1"
    
    # Option 2: Local LLM (Ollama, LM Studio, etc.)
    USE_LOCAL_LLM = True
    LOCAL_LLM_URL = "http://localhost:11434/v1/chat/completions"  # Ollama default port
    LOCAL_LLM_MODEL = "llama3.2"  # Model name in Ollama (change to your model)
    
    # Option 3: Azure OpenAI
    USE_AZURE = False
    AZURE_ENDPOINT = ""
    AZURE_API_KEY = ""
    AZURE_DEPLOYMENT = ""
    
    # Response settings
    TEMPERATURE = 0.7
    MAX_TOKENS = 500
    TIMEOUT = 30  # seconds


async def call_llm(user_input: str, system_prompt: str) -> Dict[str, Any]:
    """
    Call your LLM API and return structured response.
    
    Args:
        user_input: User's command/question
        system_prompt: System prompt for the LLM
        
    Returns:
        Dict with 'intent', 'response', and optional 'action'
    """
    
    # ====================
    # OPENAI API
    # ====================
    if LLMConfig.USE_OPENAI:
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {LLMConfig.OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "model": LLMConfig.OPENAI_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_input}
                    ],
                    "temperature": LLMConfig.TEMPERATURE,
                    "max_tokens": LLMConfig.MAX_TOKENS
                }
                
                async with session.post(
                    f"{LLMConfig.OPENAI_BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=LLMConfig.TIMEOUT)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        llm_response = data["choices"][0]["message"]["content"]
                        
                        # Parse JSON response from LLM
                        try:
                            return json.loads(llm_response)
                        except json.JSONDecodeError:
                            # Fallback if LLM doesn't return JSON
                            return {
                                "intent": "CHAT",
                                "response": llm_response,
                                "action": None
                            }
                    else:
                        logger.error(f"OpenAI API error: {resp.status}")
                        raise Exception(f"API error: {resp.status}")
                        
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            return {
                "intent": "ERROR",
                "response": "Sorry, I'm having trouble connecting to my brain right now.",
                "action": None
            }
    
    # ====================
    # LOCAL LLM (Ollama, LM Studio, etc.)
    # ====================
    elif LLMConfig.USE_LOCAL_LLM:
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                headers = {"Content-Type": "application/json"}
                
                payload = {
                    "model": LLMConfig.LOCAL_LLM_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_input}
                    ],
                    "temperature": LLMConfig.TEMPERATURE,
                    "max_tokens": LLMConfig.MAX_TOKENS
                }
                
                async with session.post(
                    LLMConfig.LOCAL_LLM_URL,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=LLMConfig.TIMEOUT)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        llm_response = data["choices"][0]["message"]["content"]
                        
                        # Parse JSON response from LLM
                        try:
                            return json.loads(llm_response)
                        except json.JSONDecodeError:
                            # Fallback if LLM doesn't return JSON
                            return {
                                "intent": "CHAT",
                                "response": llm_response,
                                "action": None
                            }
                    else:
                        logger.error(f"Local LLM error: {resp.status}")
                        raise Exception(f"API error: {resp.status}")
                        
        except Exception as e:
            logger.error(f"Local LLM call failed: {e}")
            # Fall through to mock mode
            pass
    
    # ====================
    # MOCK MODE (Fallback)
    # ====================
    logger.info("🧠 Using mock brain (configure LLM in LLMConfig)")
    
    user_lower = user_input.lower()
    
    if "time" in user_lower:
        current_time = datetime.now().strftime("%I:%M %p")
        return {
            "intent": "CHAT",
            "response": f"The current time is {current_time}.",
            "action": None
        }
    elif "date" in user_lower:
        current_date = datetime.now().strftime("%A, %B %d, %Y")
        return {
            "intent": "CHAT",
            "response": f"Today is {current_date}.",
            "action": None
        }
    elif "hello" in user_lower or "hi" in user_lower or "hey" in user_lower:
        return {
            "intent": "CHAT",
            "response": "Hello! How can I help you today?",
            "action": None
        }
    elif "weather" in user_lower:
        return {
            "intent": "BROWSER",
            "response": "I can search for the weather. What's your location?",
            "action": {"type": "browser", "query": "weather"}
        }
    elif "file" in user_lower or "folder" in user_lower or "drive" in user_lower:
        return {
            "intent": "FILE_SYSTEM",
            "response": "I can help with files. Which folder would you like to access?",
            "action": {"type": "file_system", "path": None}
        }
    elif "thank" in user_lower:
        return {
            "intent": "CHAT",
            "response": "You're welcome! Anything else I can help with?",
            "action": None
        }
    elif "bye" in user_lower or "goodbye" in user_lower or "exit" in user_lower or "quit" in user_lower:
        return {
            "intent": "CHAT",
            "response": "Goodbye! Say the wake word to activate me again.",
            "action": {"type": "exit"}
        }
    else:
        return {
            "intent": "CHAT",
            "response": f"I heard '{user_input}'. I'm still learning. Try asking about the time, date, or weather!",
            "action": None
        }


# ============================================================================
# JARVIS STATE MACHINE
# ============================================================================

class JarvisState(Enum):
    """State machine for Jarvis assistant."""
    IDLE = "idle"
    ACTIVE = "active"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"


class Jarvis:
    """
    Main Jarvis voice assistant.
    """
    
    def __init__(
        self,
        use_cuda: bool = True,
        tts_model_path: str = "models/en_US-ryan-high.onnx",
        active_window_seconds: float = 5.0
    ):
        """Initialize Jarvis."""
        logger.info("=" * 70)
        logger.info("JARVIS - AI Voice Assistant")
        logger.info("=" * 70)
        logger.info("")
        
        self.active_window = active_window_seconds
        self.state = JarvisState.IDLE
        self.last_interaction_time = 0.0
        self.is_running = False
        
        # Initialize STT with optimized latency settings
        logger.info("🎤 Loading speech recognition...")
        device = "cuda" if use_cuda and torch.cuda.is_available() else "cpu"
        compute_type = "int8" if device == "cuda" else "int8"
        logger.info(f"   STT Device: {device} | Compute: {compute_type}")
        
        self.stt = STTService(
            model_size="distil-medium.en",
            device=device,
            compute_type=compute_type,
            min_silence_duration_ms=800,  # Reduced from 1500ms for faster cutoff
            min_speech_duration_ms=200,   # Minimum speech to trigger
            vad_threshold=0.6             # Slightly more sensitive VAD
        )
        
        # Initialize Wake Word Engine BEFORE TTS to avoid PyAudio threading issues
        logger.info("🎯 Loading wake word detection...")
        try:
            # Note: Using "hey_mycroft" model (only built-in model available)
            # This is the reliable openwakeword model, displayed as "Jarvis"
            self.wake_engine = WakeWordEngine(model_name="hey_mycroft", threshold=0.5)
            self.wake_word_available = True
            logger.info("✅ Wake word engine ready - Listening for 'Hey Jarvis'")
        except Exception as e:
            logger.error(f"❌ Wake word engine failed: {e}")
            logger.error("   Please ensure openwakeword is installed:")
            logger.error("   pip install openwakeword")
            raise
        
        # Initialize TTS AFTER wake word to avoid PyAudio conflicts
        logger.info("🔊 Loading text-to-speech...")
        try:
            self.tts = TTSService(
                model_path=tts_model_path,
                use_cuda=use_cuda
            )
            self.tts_available = True
        except (FileNotFoundError, RuntimeError) as e:
            logger.warning(f"⚠️ TTS not available: {e}")
            self.tts = None
            self.tts_available = False
        print()
        print("✅ All systems ready!")
        print()
    
    def _update_interaction_time(self):
        """Update last interaction timestamp."""
        self.last_interaction_time = time.time()
    
    def _is_active_window_expired(self) -> bool:
        """Check if active window has expired."""
        if self.last_interaction_time == 0:
            return True
        return (time.time() - self.last_interaction_time) > self.active_window
    
    async def _wait_for_wake_word(self):
        """
        Wait for wake word detection using WakeWordEngine.
        Continuously listens for "Hey Jarvis" without user input.
        """
        logger.info("💤 IDLE - Listening for 'Hey Jarvis'...")
        
        # Create event to signal wake word detection
        wake_event = asyncio.Event()
        
        async def on_wake():
            logger.info("🔔 Wake callback triggered!")
            wake_event.set()
        
        # Start wake word detection in background task
        wake_task = asyncio.create_task(
            self.wake_engine.start_listening_async(on_wake)
        )
        
        try:
            # Wait for wake word detection (this will block until detected)
            await wake_event.wait()
            logger.info("🎙️ Wake word detected! Transitioning to active mode...")
        except Exception as e:
            logger.error(f"❌ Error waiting for wake word: {e}")
            raise
        finally:
            # Stop wake word engine (if not already stopped)
            try:
                self.wake_engine.stop_listening()
            except Exception as e:
                logger.warning(f"Warning during wake engine stop: {e}")
            
            # Cancel the wake word task if still running
            if not wake_task.done():
                wake_task.cancel()
                try:
                    await wake_task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.warning(f"Warning during task cancellation: {e}")
    
    async def _listen_for_command(self) -> Optional[str]:
        """Listen for user command with VAD."""
        logger.info("🎧 Listening...")
        
        try:
            transcription = await self.stt.transcribe_stream(duration_seconds=20)
            
            if transcription and transcription.strip():
                logger.info(f"📝 You: '{transcription}'")
                return transcription.strip()
            else:
                logger.warning("⚠️ No speech detected")
                return None
                
        except Exception as e:
            logger.error(f"❌ Listening error: {e}")
            return None
    
    async def _execute_mcp_tools(self, action: Optional[Dict[str, Any]]) -> Optional[str]:
        """
        Execute MCP tools based on LLM action request.
        This is the integration point for your MCP server.
        
        Args:
            action: Action dictionary from LLM (includes type and parameters)
            
        Returns:
            Tool execution result (optional, for context)
        """
        if not action:
            return None
        
        action_type = action.get("type")
        logger.info(f"🔧 MCP Tool Request: {action_type}")
        
        # TODO: Connect to your MCP server here
        # Example:
        # async with aiohttp.ClientSession() as session:
        #     mcp_payload = {
        #         "tool": action_type,
        #         "parameters": action.get("parameters", {})
        #     }
        #     async with session.post("http://localhost:8080/execute", json=mcp_payload) as resp:
        #         result = await resp.json()
        #         return result.get("output")
        
        # For now, handle basic actions locally
        if action_type == "exit":
            self.is_running = False
            return "Shutting down"
        
        return None
    
    async def _speak_with_barge_in(self, text: str, monitor_speech: bool = True):
        """
        Speak text with barge-in support - stops if user starts talking.
        
        Args:
            text: Text to speak
            monitor_speech: Whether to monitor for user speech during playback
        """
        if not self.tts_available:
            print(f"🤖 JARVIS: {text}")
            return
        
        # Start TTS playback (non-blocking)
        self.tts.speak_async(text)
        
        if not monitor_speech:
            # Just wait for completion without monitoring (async)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.tts.wait_until_done)
            return
        
        # Monitor for user speech while TTS is playing
        import pyaudio
        audio = pyaudio.PyAudio()
        stream = None
        
        try:
            stream = audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=512
            )
            
            logger.info("🎯 Monitoring for barge-in...")
            
            # Check for speech while TTS is playing
            while self.tts.is_speaking:
                # Read audio chunk
                loop = asyncio.get_event_loop()
                
                def read_audio():
                    return stream.read(512, exception_on_overflow=False)
                
                audio_data = await loop.run_in_executor(None, read_audio)
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                
                # Check for speech
                speech_prob = await loop.run_in_executor(
                    None,
                    self.stt.detect_speech,
                    audio_array
                )
                
                # If user starts speaking, interrupt TTS
                if speech_prob > 0.7:  # Higher threshold for barge-in
                    logger.info("🛑 User speaking detected - stopping TTS")
                    self.tts.stop_speaking()
                    break
                
                # Small delay to avoid busy-waiting
                await asyncio.sleep(0.01)
            
        except Exception as e:
            logger.warning(f"⚠️ Barge-in monitoring error: {e}")
        finally:
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except:
                    pass
            try:
                audio.terminate()
            except:
                pass
    
    async def _process_command(self, user_input: str):
        """Process command through LLM → MCP Tools → TTS pipeline."""
        self.state = JarvisState.PROCESSING
        
        # Step 1: Get LLM response (structured JSON)
        result = await call_llm(user_input, get_router_prompt())
        
        intent = result.get("intent", "UNKNOWN")
        response = result.get("response", "I'm not sure how to respond.")
        action = result.get("action")
        
        logger.info(f"💡 Intent: {intent}")
        logger.info(f"📦 LLM Response: {json.dumps(result, indent=2)}")
        
        # Step 2: Execute MCP tools if action required
        tool_result = None
        if action:
            tool_result = await self._execute_mcp_tools(action)
            if tool_result:
                # Update response with tool result
                response = f"{response} {tool_result}"
                logger.info(f"🔧 Tool Result: {tool_result}")
        
        logger.info(f"💬 Jarvis: {response}")
        
        # Step 3: Speak response with barge-in monitoring
        self.state = JarvisState.SPEAKING
        await self._speak_with_barge_in(response, monitor_speech=True)
        
        # Update interaction time
        self._update_interaction_time()
    
    async def _active_loop(self):
        """Active state - stays awake for follow-up commands."""
        try:
            self.state = JarvisState.ACTIVE
            self._update_interaction_time()
            
            print()
            print("=" * 70)
            print(f"⏰ Active for {self.active_window}s - Speak your command")
            print("=" * 70)
            print()
            
            # Acknowledgment
            logger.info("🔊 Speaking acknowledgment...")
            await self._speak_with_barge_in("Yes?", monitor_speech=False)
            logger.info("✅ Acknowledgment complete")
            await asyncio.sleep(0.3)
            
            while self.is_running:
                # Check timeout
                if self._is_active_window_expired():
                    logger.info(f"⏱️ {self.active_window}s timeout - going back to sleep")
                    return
                
                # Listen for command
                self.state = JarvisState.LISTENING
                user_input = await self._listen_for_command()
                
                if user_input:
                    # Process command
                    await self._process_command(user_input)
                    
                    if not self.is_running:
                        return
                    
                    # Ready for follow-up
                    remaining = self.active_window - (time.time() - self.last_interaction_time)
                    logger.info(f"⏰ Ready for follow-up ({remaining:.1f}s remaining)")
                    self.state = JarvisState.ACTIVE
                else:
                    # No speech - check if still in window
                    if self._is_active_window_expired():
                        logger.info("⏱️ No input - going back to sleep")
                        return
        except Exception as e:
            logger.error(f"❌ Error in active loop: {e}", exc_info=True)
            raise
    
    async def run(self):
        """Main loop."""
        self.is_running = True
        
        logger.info("")
        logger.info("Jarvis is ready!")
        logger.info("After wake word: You have 5 seconds for follow-up commands")
        logger.info("Say 'goodbye' or 'exit' to shut down")
        logger.info("")
        
        try:
            while self.is_running:
                try:
                    # Wait for wake word
                    self.state = JarvisState.IDLE
                    await self._wait_for_wake_word()
                    
                    if not self.is_running:
                        break
                    
                    # Enter active mode
                    logger.info("📍 Entering active loop...")
                    await self._active_loop()
                    logger.info("📍 Exited active loop, returning to idle...")
                    
                except Exception as e:
                    logger.error(f"❌ Error in main loop: {e}", exc_info=True)
                    logger.info("Recovering... returning to idle state")
                    await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("\n⚠️ Interrupted by user")
        except Exception as e:
            logger.error(f"❌ Fatal error: {e}", exc_info=True)
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Clean shutdown."""
        logger.info("")
        logger.info("Shutting down Jarvis...")
        
        self.is_running = False
        
        if self.tts_available and self.tts:
            self.tts.shutdown()
            logger.info("TTS stopped")
        
        logger.info("Goodbye!")


# ============================================================================
# ENTRY POINT
# ============================================================================

async def main():
    """Start Jarvis."""
    
    # Configuration
    jarvis = Jarvis(
        use_cuda=True,
        tts_model_path="models/en_US-ryan-high.onnx",
        active_window_seconds=5.0
    )
    
    # Run
    await jarvis.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Jarvis terminated")
