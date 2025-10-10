"""Configuration management"""

import os
import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class AudioConfig:
    """Audio configuration"""
    sample_rate: int
    channels: int
    chunk_size: int
    input_device: Optional[int]
    output_device: Optional[int]

@dataclass
class WakeWordConfig:
    """Wake word configuration"""
    keywords: List[str]
    threshold: float

@dataclass
class STTConfig:
    """Speech-to-text configuration"""
    engine: str
    model: str
    language: str
    cache_enabled: bool

@dataclass
class TTSConfig:
    """Text-to-speech configuration"""
    engine: str
    voice: str
    rate: float
    streaming: bool

@dataclass
class ResponseConfig:
    """Response configuration"""
    acknowledge_sound: Optional[str]
    error_sound: Optional[str]
    fallback_messages: List[str]

@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str
    format: str
    file: Optional[str]

@dataclass
class Config:
    """Main configuration"""
    audio: AudioConfig
    wake_word: WakeWordConfig
    stt: STTConfig
    tts: TTSConfig
    response: ResponseConfig
    logging: LoggingConfig

def load_config(config_path: str = "config/config.yaml") -> Config:
    """Load configuration from YAML file"""
    path = Path(config_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    return Config(
        audio=AudioConfig(**data['audio']),
        wake_word=WakeWordConfig(**data['wake_word']),
        stt=STTConfig(**data['stt']),
        tts=TTSConfig(**data['tts']),
        response=ResponseConfig(**data['response']),
        logging=LoggingConfig(**data['logging'])
    )
