"""
Custom exceptions for the voice assistant application
"""


class VoiceAssistantError(Exception):
    """Base exception for voice assistant errors"""
    pass


class ConfigurationError(VoiceAssistantError):
    """Raised when configuration is invalid or missing"""
    pass


class ContainerInitializationError(VoiceAssistantError):
    """Raised when dependency injection container fails to initialize"""
    pass


class AudioError(VoiceAssistantError):
    """Raised when audio input/output fails"""
    pass


class WakeWordError(VoiceAssistantError):
    """Raised when wake word detection fails"""
    pass


class STTError(VoiceAssistantError):
    """Raised when speech-to-text conversion fails"""
    pass


class AIError(VoiceAssistantError):
    """Raised when AI model processing fails"""
    pass


class LocationError(VoiceAssistantError):
    """Raised when location detection fails"""
    pass
