"""Voice Assistant - BIP Phase (Testing Mode)"""
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
            device=config.audio.input_device
        )
        
        self.wake_word = OpenWakeWordDetector(
            keywords=config.wake_word.keywords,
            threshold=config.wake_word.threshold
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
        """Main loop - TESTING MODE"""
        logger.info("voice_assistant_ready")
        print("\n" + "="*60)
        print("🎤 TESTING MODE - Press Enter to activate")
        print("="*60 + "\n")
        
        while True:
            try:
                print("Press Enter to start...")
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, input)
                
                logger.info("activated")
                print("\n✨ Listening for command...\n")
                
                command_text = await loop.run_in_executor(
                    None, 
                    lambda: input("Type your command: ")
                )
                
                if not command_text or len(command_text.strip()) == 0:
                    print("❌ Empty command\n")
                    continue
                
                logger.info("command_received", text=command_text)
                print(f"\n📝 You: {command_text}")
                
                # Delegate to command handler
                response = self.process_command(command_text)
                
                logger.info("responding", response=response)
                print(f"🤖 Bot: {response}\n")
                print("-"*60 + "\n")
                
            except KeyboardInterrupt:
                raise
            except Exception as e:
                logger.error("processing_error", error=str(e))
                print(f"❌ Error: {e}\n")
    
    def process_command(self, text: str) -> str:
        """Delegate command processing to CommandHandler"""
        return self.command_handler.process(text)
    
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("cleaning_up")


async def main():
    """Main entry point"""
    try:
        config = load_config()
        setup_logging(
            level=config.logging.level,
            log_format=config.logging.format,
            log_file=config.logging.file
        )
        
        logger.info("application_starting", version="0.1.0", phase="BIP-TEST")
        
        print("\n🤖 Voice Assistant - Testing Mode")
        print("ℹ️  Enter = wake word | Text = voice\n")
        
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