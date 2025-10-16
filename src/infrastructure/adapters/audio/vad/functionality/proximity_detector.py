# src/infrastructure/adapters/audio/vad/functionality/proximity_detector.py

"""Proximity detection - detects if speaker is close enough."""

import numpy as np
import structlog
from typing import Optional

logger = structlog.get_logger()


class ProximityDetector:
    """
    Detekuje jestli je mluvčí dostatečně blízko.
    Odfiltruje vzdálený TV, ostatní lidi v místnosti.

    Princip:
    - Kalibruje se na background noise
    - Vyžaduje aby zvuk byl X krát hlasitější než pozadí
    - S marginem pro fluktuace hlasitosti
    """

    def __init__(
            self,
            threshold_multiplier: float = 3.0,
            margin: float = 0.8,
            enabled: bool = True
    ):
        """
        Args:
            threshold_multiplier: Kolikrát hlasitější než pozadí (default 3x)
            margin: Margin pro fluktuace (0.8 = 80% threshold, tolerance 20%)
            enabled: Enable/disable proximity check
        """
        self.threshold_multiplier = threshold_multiplier
        self.margin = margin
        self.enabled = enabled

        self.background_noise: float = 0.0
        self.calibrated = False

        logger.debug(
            "proximity_detector_initialized",
            threshold_multiplier=threshold_multiplier,
            margin=margin,
            enabled=enabled
        )

    def calibrate(self, noise_level: float) -> None:
        """
        Nastav background noise level.

        Args:
            noise_level: Průměrná hlasitost pozadí (0.0-1.0)
        """
        self.background_noise = noise_level
        self.calibrated = True

        threshold = self.get_threshold()

        logger.info(
            "proximity_calibrated",
            background=round(noise_level, 6),
            threshold=round(threshold, 6),
            multiplier=self.threshold_multiplier
        )

    def get_threshold(self) -> float:
        """
        Vypočítej aktuální threshold s marginem.

        Returns:
            Threshold pro proximity check
        """
        base_threshold = self.background_noise * self.threshold_multiplier
        return base_threshold * self.margin

    def is_close_enough(self, frame: np.ndarray) -> bool:
        """
        Zkontroluj jestli je frame dostatečně blízko.

        Args:
            frame: Audio frame (numpy array)

        Returns:
            True pokud je dostatečně blízko (nebo proximity disabled)
        """
        if not self.enabled:
            return True

        if not self.calibrated:
            # Bez kalibrace přijmi vše
            logger.debug("proximity_check_skipped_not_calibrated")
            return True

        volume = float(np.abs(frame).mean())
        threshold = self.get_threshold()

        is_close = volume >= threshold

        if not is_close:
            logger.debug(
                "proximity_rejected",
                volume=round(volume, 6),
                threshold=round(threshold, 6),
                distance=self.get_distance_estimate(frame)
            )

        return is_close

    def get_distance_estimate(self, frame: np.ndarray) -> str:
        """
        Odhadni vzdálenost mluvčího podle hlasitosti.

        Args:
            frame: Audio frame

        Returns:
            "very_close", "close", "medium", "far", "very_far", "unknown"
        """
        if not self.calibrated:
            return "unknown"

        if self.background_noise <= 0:
            return "unknown"

        volume = float(np.abs(frame).mean())
        ratio = volume / self.background_noise

        # Klasifikace podle ratio
        if ratio >= 10.0:
            return "very_close"  # 10x hlasitější = přímo u mikrofonu
        elif ratio >= 5.0:
            return "close"  # 5x hlasitější = blízko
        elif ratio >= 3.0:
            return "medium"  # 3x hlasitější = normální vzdálenost
        elif ratio >= 1.5:
            return "far"  # 1.5x hlasitější = daleko
        else:
            return "very_far"  # < 1.5x = velmi daleko (TV, jiný pokoj)

    def get_volume_ratio(self, frame: np.ndarray) -> float:
        """
        Vypočítej ratio volume vs. background.

        Args:
            frame: Audio frame

        Returns:
            Ratio (0.0 = stejná hlasitost, 10.0 = 10x hlasitější)
        """
        if not self.calibrated or self.background_noise <= 0:
            return 0.0

        volume = float(np.abs(frame).mean())
        return volume / self.background_noise

    def reset_calibration(self) -> None:
        """Resetuj kalibraci (pro re-calibrate)."""
        self.background_noise = 0.0
        self.calibrated = False
        logger.info("proximity_calibration_reset")
