"""Voice Assistant - BIP Phase (Voice Mode)"""

import asyncio
import os
import structlog
from dotenv import load_dotenv
from src.core.config import load_config
from src.core.logger import setup_logging
from src.audio.capture import AudioCapture
from src.audio.player import AudioPlayer
from src.wake_word.detector import OpenWakeWordDetector
from src.stt.whisper_engine import WhisperSTT
from src.commands.handler import CommandHandler
from src.tts.piper_engine import PiperTTS
from src.response.handler import ResponseHandler

load_dotenv()
logger = structlog.get_logger()

class VoiceAssistant:
    """Main Voice Assistant class"""
    
    def __init__(self, config):
        self.config = config
        logger.info("initializing_voice_assistant")
        
        # Command handler for business logic
        self.command_handler = CommandHandler()
        
        self.audio_capture = AudioCapture(
            sample_rate=config.audio.sample_rate,
            channels=config.audio.channels,
            chunk_size=config.audio.chunk_size,
            device=config.audio.input_device,
            gain=2.5  # Zvýšená citlivost mikrofonu (2.5x)
        )
        
        self.wake_word = OpenWakeWordDetector(
            keywords=config.wake_word.keywords,
            threshold=0.3  # Fixed at 0.3 for better detection
        )
        
        self.stt = WhisperSTT(
            model_size=config.stt.model,
            language=config.stt.language
        )
        
        self.tts = PiperTTS(
            voice=config.tts.voice,
            rate=config.tts.rate
        )
        
        self.response_handler = ResponseHandler(
            tts_engine=self.tts,
            acknowledge_sound=config.response.acknowledge_sound,
            error_sound=config.response.error_sound
        )
    
    async def start(self):
        """Start the assistant"""
        logger.info("voice_assistant_starting")
        try:
            await self.run()
        except KeyboardInterrupt:
            logger.info("voice_assistant_stopping")
        except Exception as e:
            logger.error("voice_assistant_error", error=str(e), exc_info=True)
            raise
        finally:
            await self.cleanup()
    
    async def run(self):
        """Main loop - VOICE MODE with Wake Word"""
        logger.info("voice_assistant_ready")
        print("\n" + "="*60)
        print("🎤 VOICE MODE - Say 'Alexa' to activate")
        print("="*60 + "\n")
        
        # Start audio capture stream
        try:
            audio_stream = self.audio_capture.start_stream()
        except Exception as e:
            logger.error("failed_to_start_audio_stream", error=str(e))
            print(f"❌ Failed to start microphone: {e}")
            return
        
        while True:
            try:
                logger.info("listening_for_wake_word")
                print("👂 Listening for wake word...")
                
                # Wait for wake word detection
                detected = await self._wait_for_wake_word(audio_stream)
                
                if detected:
                    logger.info("wake_word_detected")
                    print("\n✨ Wake word detected!")
                    print("💬 Say your command now (5 seconds)...\n")
                    
                    # Small delay to avoid capturing the wake word
                    await asyncio.sleep(0.3)
                    
                    # Capture audio after wake word (zvýšeno na 5 sekund)
                    audio_data = await self.audio_capture.record_command(duration=5.0)
                    
                    # Show recording feedback
                    print("🔄 Processing your command...\n")
                    
                    # Fixed: Proper numpy array check
                    if audio_data is None or len(audio_data) == 0:
                        print("❌ No audio captured\n")
                        continue
                    
                    # Convert speech to text
                    logger.info("transcribing_audio")
                    command_text = await self.stt.transcribe(audio_data)
                    
                    if not command_text or len(command_text.strip()) == 0:
                        print("❌ No command detected\n")
                        print("-"*60 + "\n")
                        # Cooldown period
                        await asyncio.sleep(2)
                        continue
                    
                    # Show what was heard
                    logger.info("command_received", text=command_text)
                    print(f"📝 You said: \"{command_text}\"")
                    print(f"⏱️  Processing...\n")
                    
                    # Process command
                    response = self.process_command(command_text)
                    
                    logger.info("responding", response=response)
                    print(f"🤖 Bot: {response}\n")
                    print("-"*60 + "\n")
                    
                    # Cooldown to prevent false triggers from bot's response
                    await asyncio.sleep(2)
                    
            except KeyboardInterrupt:
                raise
            except Exception as e:
                logger.error("processing_error", error=str(e), exc_info=True)
                print(f"❌ Error: {e}\n")
                # Cooldown after error
                await asyncio.sleep(1)
    
    async def _wait_for_wake_word(self, audio_stream):
        """Wait for wake word detection"""
        while True:
            try:
                audio_chunk = await self.audio_capture.read_chunk(audio_stream)
                if self.wake_word.detect(audio_chunk):
                    return True
                await asyncio.sleep(0.01)  # Prevent CPU hogging
            except Exception as e:
                logger.error("wake_word_detection_error", error=str(e))
                await asyncio.sleep(0.1)
    
    def process_command(self, text: str) -> str:
        """Delegate command processing to CommandHandler"""
        return self.command_handler.process(text)
    
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("cleaning_up")
        try:
            self.audio_capture.stop_stream()
        except Exception as e:
            logger.error("cleanup_error", error=str(e))

async def main():
    """Main entry point"""
    try:
        config = load_config()
        setup_logging(
            level=config.logging.level,
            log_format=config.logging.format,
            log_file=config.logging.file
        )
        
        logger.info("application_starting", version="0.1.0", phase="VOICE-MODE")
        print("\n🤖 Voice Assistant - Voice Mode")
        print("ℹ️  Say wake word to activate\n")
        
        assistant = VoiceAssistant(config)
        await assistant.start()
        
    except FileNotFoundError as e:
        print(f"❌ Config error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!\n")
