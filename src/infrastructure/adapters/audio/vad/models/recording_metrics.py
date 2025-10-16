# src/infrastructure/adapters/audio/vad/models/recording_metrics.py

"""Recording metrics model."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class RecordingMetrics:
    """
    Metriky pro nahrávání.
    Poskytuje detailní statistiky o kvalitě a výkonu.
    """

    # ========================================
    # Timing
    # ========================================
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None

    # ========================================
    # Frame statistics
    # ========================================
    total_frames: int = 0  # Celkový počet framů
    speech_frames: int = 0  # Počet framů s řečí
    silence_frames: int = 0  # Počet framů s tichem
    proximity_rejected_frames: int = 0  # Odmítnuto proximity checkm
    quality_rejected_frames: int = 0  # Odmítnuto quality checkem

    # ========================================
    # Audio statistics
    # ========================================
    total_samples: int = 0  # Celkový počet samples
    avg_volume: float = 0.0  # Průměrná hlasitost (0.0-1.0)
    peak_volume: float = 0.0  # Špičková hlasitost
    min_volume: float = 1.0  # Minimální hlasitost
    background_noise: float = 0.0  # Úroveň pozadí

    # ========================================
    # Quality indicators
    # ========================================
    clipping_detected: bool = False  # Detekován clipping
    too_quiet: bool = False  # Příliš tiché audio

    # ========================================
    # Performance
    # ========================================
    processing_time_ms: float = 0.0  # Čas zpracování (ms)

    # ========================================
    # Meta
    # ========================================
    stop_reason: str = "unknown"  # Důvod ukončení

    # ========================================
    # Computed properties
    # ========================================

    @property
    def duration_seconds(self) -> float:
        """Celková délka nahrávání v sekundách."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return (datetime.now() - self.start_time).total_seconds()

    @property
    def speech_ratio(self) -> float:
        """
        Poměr řeči vs. ticha (0.0-1.0).
        1.0 = pouze řeč, 0.0 = pouze ticho.
        """
        if self.total_frames == 0:
            return 0.0
        return self.speech_frames / self.total_frames

    @property
    def effective_frames(self) -> int:
        """Počet framů po filtrování (použitých pro nahrávku)."""
        return self.total_frames - self.proximity_rejected_frames - self.quality_rejected_frames

    @property
    def rejection_rate(self) -> float:
        """
        Procento odmítnutých framů (0.0-1.0).
        Vysoká hodnota = hodně šumu/vzdáleného zvuku.
        """
        if self.total_frames == 0:
            return 0.0
        rejected = self.proximity_rejected_frames + self.quality_rejected_frames
        return rejected / self.total_frames

    @property
    def snr_estimate(self) -> float:
        """
        Odhad Signal-to-Noise Ratio.
        Vyšší = lepší kvalita.
        """
        if self.background_noise <= 0:
            return 0.0
        if self.avg_volume <= 0:
            return 0.0
        return self.avg_volume / self.background_noise

    @property
    def quality_score(self) -> float:
        """
        Celkové quality score (0.0-1.0).
        Kombinuje speech ratio, SNR, rejection rate.
        """
        if self.total_frames == 0:
            return 0.0

        # Komponenty
        speech_score = self.speech_ratio  # 0.0-1.0
        snr_score = min(1.0, self.snr_estimate / 10.0)  # Normalizuj SNR
        rejection_score = 1.0 - self.rejection_rate  # Inverzní

        # Weighted average
        score = (speech_score * 0.4 + snr_score * 0.3 + rejection_score * 0.3)

        # Penalties
        if self.clipping_detected:
            score *= 0.8
        if self.too_quiet:
            score *= 0.8

        return max(0.0, min(1.0, score))

    # ========================================
    # Export
    # ========================================

    def to_dict(self) -> dict:
        """Export pro logging a analytics."""
        return {
            # Timing
            'duration_s': round(self.duration_seconds, 2),
            'processing_time_ms': round(self.processing_time_ms, 2),

            # Frames
            'total_frames': self.total_frames,
            'speech_frames': self.speech_frames,
            'silence_frames': self.silence_frames,
            'effective_frames': self.effective_frames,
            'speech_ratio': round(self.speech_ratio, 3),

            # Rejection
            'proximity_rejected': self.proximity_rejected_frames,
            'quality_rejected': self.quality_rejected_frames,
            'rejection_rate': round(self.rejection_rate, 3),

            # Audio
            'avg_volume': round(self.avg_volume, 4),
            'peak_volume': round(self.peak_volume, 4),
            'min_volume': round(self.min_volume, 4),
            'background_noise': round(self.background_noise, 4),
            'snr_estimate': round(self.snr_estimate, 2),

            # Quality
            'quality_score': round(self.quality_score, 3),
            'clipping_detected': self.clipping_detected,
            'too_quiet': self.too_quiet,

            # Meta
            'stop_reason': self.stop_reason,
            'samples': self.total_samples
        }

    def __str__(self) -> str:
        """Human-readable summary."""
        return (
            f"Recording: {self.duration_seconds:.1f}s, "
            f"speech={self.speech_ratio:.0%}, "
            f"quality={self.quality_score:.0%}, "
            f"reason={self.stop_reason}"
        )
