"""Custom exceptions for Voice Assistant"""

class VoiceAssistantException(Exception):
    """Base exception for Voice Assistant"""
    pass

class AudioCaptureError(VoiceAssistantException):
    """Raised when audio capture fails"""
    pass

class WakeWordError(VoiceAssistantException):
    """Raised when wake word detection fails"""
    pass

class STTError(VoiceAssistantException):
    """Raised when STT fails"""
    pass

class TTSError(VoiceAssistantException):
    """Raised when TTS fails"""
    pass

class ConfigurationError(VoiceAssistantException):
    """Raised when configuration is invalid"""
    pass
