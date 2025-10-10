"""Configuration management"""
import os
from pathlib import Path
from typing import Any, Dict
import yaml
from dataclasses import dataclass


@dataclass
class AudioConfig:
    sample_rate: int
    channels: int
    chunk_size: int
    input_device: str = None
    output_device: str = None


@dataclass
class WakeWordConfig:
    keywords: list
    threshold: float


@dataclass
class STTConfig:
    engine: str
    model: str
    language: str
    cache_enabled: bool


@dataclass
class TTSConfig:
    engine: str
    voice: str
    rate: float
    streaming: bool


@dataclass
class ResponseConfig:
    acknowledge_sound: str
    error_sound: str
    fallback_messages: list


@dataclass
class LoggingConfig:
    level: str
    format: str
    file: str


@dataclass
class Config:
    audio: AudioConfig
    wake_word: WakeWordConfig
    stt: STTConfig
    tts: TTSConfig
    response: ResponseConfig
    logging: LoggingConfig


def load_config(config_path: str = "config/config.yaml") -> Config:
    """Load configuration from YAML file"""
    if not Path(config_path).exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    return Config(
        audio=AudioConfig(**data['audio']),
        wake_word=WakeWordConfig(**data['wake_word']),
        stt=STTConfig(**data['stt']),
        tts=TTSConfig(**data['tts']),
        response=ResponseConfig(**data['response']),
        logging=LoggingConfig(**data['logging'])
    )
