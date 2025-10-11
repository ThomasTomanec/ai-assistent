"""
Groq Whisper STT adapter - super rychlý a zdarma!
"""

import structlog
import io
import wave
from groq import Groq
from src.core.ports.i_stt_engine import ISTTEngine

logger = structlog.get_logger()

class GroqWhisperAdapter(ISTTEngine):
    """
    STT adapter pro Groq Whisper API.
    Extrémně rychlý (0.1-0.3s latence) a zdarma.
    """
    
    def __init__(self, api_key: str, language: str = "cs", sample_rate: int = 16000):
        """
        Args:
            api_key: Groq API klíč
            language: Jazyk pro rozpoznávání (cs = čeština)
            sample_rate: Sample rate audia (16000 Hz)
        """
        self.client = Groq(api_key=api_key)
        self.language = language
        self.sample_rate = sample_rate
        logger.info("groq_whisper_initialized", language=language, sample_rate=sample_rate)
    
    def _convert_to_wav(self, audio_data: bytes) -> bytes:
        """
        Převede raw PCM audio na WAV formát s hlavičkami.
        
        Args:
            audio_data: Raw PCM audio data (int16)
            
        Returns:
            WAV audio data s hlavičkami
        """
        wav_buffer = io.BytesIO()
        
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit = 2 bytes
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(audio_data)
        
        return wav_buffer.getvalue()
    
    async def transcribe(self, audio_data: bytes) -> str:
        """
        Převede zvuk na text pomocí Groq Whisper.
        
        Args:
            audio_data: Audio data (raw PCM)
            
        Returns:
            Rozpoznaný text
        """
        try:
            logger.info("groq_transcribing", size=len(audio_data))
            
            # Převeď raw PCM na WAV formát
            wav_data = self._convert_to_wav(audio_data)
            
            # Vytvoř file-like objekt
            audio_file = io.BytesIO(wav_data)
            audio_file.name = "audio.wav"
            
            # Zavolej Groq Whisper API
            transcription = self.client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-large-v3-turbo",  # Nejrychlejší model
                language=self.language,
                response_format="text"
            )
            
            text = transcription.strip()
            logger.info("groq_complete", text=text[:100])
            
            return text
            
        except Exception as e:
            logger.error("groq_transcription_error", error=str(e))
            return ""
