# src/infrastructure/adapters/audio/vad/functionality/audio_validator.py

"""Audio quality validation."""

import numpy as np
import structlog

logger = structlog.get_logger()


class AudioValidator:
    """
    Validuje kvalitu audio framů.
    Odfiltruje:
    - Šum (příliš tiché)
    - Clipping (příliš hlasité)
    - Noise gate (pod threshold)
    """

    def __init__(
            self,
            min_volume: float = 0.001,
            max_volume: float = 0.95,
            noise_gate_enabled: bool = True,
            noise_gate_ratio: float = 1.5
    ):
        """
        Args:
            min_volume: Minimální akceptovatelná hlasitost (0.001 = 0.1%)
            max_volume: Maximální hlasitost (0.95 = 95%, detekce clippingu)
            noise_gate_enabled: Enable noise gate
            noise_gate_ratio: Noise gate threshold (násobek background)
        """
        self.min_volume = min_volume
        self.max_volume = max_volume
        self.noise_gate_enabled = noise_gate_enabled
        self.noise_gate_ratio = noise_gate_ratio

        self.background_noise: float = 0.0
        self.clipping_count = 0
        self.too_quiet_count = 0

        logger.debug(
            "audio_validator_initialized",
            min_volume=min_volume,
            max_volume=max_volume,
            noise_gate=noise_gate_enabled
        )

    def set_background_noise(self, noise_level: float) -> None:
        """
        Nastav background noise pro noise gate.

        Args:
            noise_level: Background noise level
        """
        self.background_noise = noise_level

        if self.noise_gate_enabled:
            gate_threshold = noise_level * self.noise_gate_ratio
            logger.info(
                "audio_validator_noise_gate_set",
                background=round(noise_level, 6),
                gate_threshold=round(gate_threshold, 6)
            )

    def validate(self, frame: np.ndarray) -> tuple[bool, str]:
        """
        Validuj audio frame.

        Args:
            frame: Audio frame (numpy array)

        Returns:
            (is_valid, reason)
            - is_valid: True pokud je frame validní
            - reason: "ok" nebo důvod odmítnutí
        """
        volume = float(np.abs(frame).mean())
        peak = float(np.abs(frame).max())

        # Check 1: Clipping (příliš hlasité)
        if peak >= self.max_volume:
            self.clipping_count += 1
            logger.debug(
                "audio_validation_failed_clipping",
                peak=round(peak, 4),
                threshold=self.max_volume
            )
            return False, "clipping"

        # Check 2: Too quiet (příliš tiché)
        if volume < self.min_volume:
            self.too_quiet_count += 1
            return False, "too_quiet"

        # Check 3: Noise gate
        if self.noise_gate_enabled and self.background_noise > 0:
            noise_threshold = self.background_noise * self.noise_gate_ratio

            if volume < noise_threshold:
                return False, "below_noise_gate"

        # Všechny checky OK
        return True, "ok"

    def get_quality_score(self, frame: np.ndarray) -> float:
        """
        Vypočítej quality score pro frame (0.0-1.0).

        Args:
            frame: Audio frame

        Returns:
            Quality score (1.0 = perfektní, 0.0 = špatné)
        """
        volume = float(np.abs(frame).mean())
        peak = float(np.abs(frame).max())

        # Ideal range: 0.01 - 0.5
        # Příliš tiché nebo příliš hlasité = nízké skóre

        if volume < 0.001:
            # Extrémně tiché
            return 0.0

        if peak > 0.95:
            # Clipping
            return 0.0

        if volume < 0.01:
            # Velmi tiché
            return volume / 0.01  # 0.0 - 1.0

        if volume > 0.5:
            # Příliš hlasité (ale ne clipping)
            return max(0.0, 1.0 - (volume - 0.5) / 0.5)  # 1.0 - 0.0

        # Perfect range (0.01 - 0.5)
        return 1.0

    def get_statistics(self) -> dict:
        """
        Vrať statistiky o validaci.

        Returns:
            Dictionary se statistikami
        """
        return {
            'clipping_count': self.clipping_count,
            'too_quiet_count': self.too_quiet_count,
            'noise_gate_enabled': self.noise_gate_enabled,
            'background_noise': round(self.background_noise, 6)
        }

    def reset_statistics(self) -> None:
        """Resetuj počítadla."""
        self.clipping_count = 0
        self.too_quiet_count = 0
