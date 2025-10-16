# src/infrastructure/adapters/audio/vad/models/recording_config.py

"""Recording configuration model with ULTRA-FAST production defaults."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RecordingConfig:
    """
    Konfigurace pro nahrávání s VAD.
    ULTRA-FAST: 0.3s trailing silence (fastest response).
    """

    # ========================================
    # Duration settings - ULTRA-FAST
    # ========================================
    max_duration: float = 15.0  # Max délka nahrávky (s)
    silence_duration: float = 1.0  # Initial silence timeout (s)
    quick_silence: float = 0.3  # 👈 ULTRA-FAST: 0.3s trailing
    min_speech_frames: int = 3  # 👈 SNÍŽENO na 3 (0.09s)

    # ========================================
    # Proximity detection (disabled for production)
    # ========================================
    proximity_enabled: bool = False
    proximity_threshold: float = 2.5
    proximity_margin: float = 0.7

    # ========================================
    # Audio quality (liberal for production)
    # ========================================
    min_volume_threshold: float = 0.0
    max_volume_threshold: float = 1.0
    noise_gate_enabled: bool = False
    noise_gate_ratio: float = 1.0

    # ========================================
    # VAD settings (legacy, not used)
    # ========================================
    vad_aggressiveness: int = 0
    sample_rate: int = 16000
    frame_duration_ms: int = 30

    # ========================================
    # Advanced features
    # ========================================
    adaptive_timeout_enabled: bool = True

    # ========================================
    # Optional metadata
    # ========================================
    name: Optional[str] = field(default=None)
    description: Optional[str] = field(default="Ultra-fast VAD config (0.3s)")

    # ========================================
    # Computed properties
    # ========================================

    @property
    def frame_size(self) -> int:
        """Vypočítej frame size v samples."""
        return int(self.sample_rate * self.frame_duration_ms / 1000)

    @property
    def silence_frames(self) -> int:
        """Kolik framů je silence_duration (initial)."""
        return int(self.silence_duration * 1000 / self.frame_duration_ms)

    @property
    def quick_silence_frames(self) -> int:
        """Kolik framů je quick_silence (trailing)."""
        return int(self.quick_silence * 1000 / self.frame_duration_ms)

    @property
    def max_frames(self) -> int:
        """Maximální počet framů."""
        return int(self.max_duration * 1000 / self.frame_duration_ms)

    @property
    def frames_per_second(self) -> int:
        """Kolik framů za sekundu."""
        return int(1000 / self.frame_duration_ms)

    @property
    def bytes_per_frame(self) -> int:
        """Kolik bytů na frame (assuming int16)."""
        return self.frame_size * 2

    @property
    def estimated_max_memory_mb(self) -> float:
        """Odhad maximální paměti pro buffer (MB)."""
        return (self.max_frames * self.bytes_per_frame) / (1024 * 1024)

    def validate(self) -> None:
        """Validuj konfiguraci."""
        if self.max_duration <= 0:
            raise ValueError("max_duration must be > 0")

        if self.silence_duration <= 0:
            raise ValueError("silence_duration must be > 0")

        if self.quick_silence <= 0:
            raise ValueError("quick_silence must be > 0")

        if self.quick_silence > self.silence_duration:
            raise ValueError("quick_silence must be <= silence_duration")

        if self.min_speech_frames < 1:
            raise ValueError("min_speech_frames must be >= 1")

        if self.sample_rate not in [8000, 16000, 32000, 48000]:
            raise ValueError("sample_rate must be 8000/16000/32000/48000")

        if self.frame_duration_ms not in [10, 20, 30]:
            raise ValueError("frame_duration_ms must be 10/20/30")

    def to_dict(self) -> dict:
        """Export config jako dictionary."""
        return {
            # Duration
            'max_duration': self.max_duration,
            'silence_duration': self.silence_duration,
            'quick_silence': self.quick_silence,
            'min_speech_frames': self.min_speech_frames,

            # Proximity
            'proximity_enabled': self.proximity_enabled,
            'proximity_threshold': self.proximity_threshold,

            # Quality
            'noise_gate_enabled': self.noise_gate_enabled,

            # VAD
            'sample_rate': self.sample_rate,
            'frame_duration_ms': self.frame_duration_ms,

            # Advanced
            'adaptive_timeout_enabled': self.adaptive_timeout_enabled,

            # Computed
            'frame_size': self.frame_size,
            'frames_per_second': self.frames_per_second,
            'estimated_max_memory_mb': round(self.estimated_max_memory_mb, 2)
        }
