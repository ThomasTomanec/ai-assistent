# src/infrastructure/adapters/audio/vad/functionality/buffer_manager.py

"""Efficient buffer management using deque."""

from collections import deque
from typing import Optional
import numpy as np
import structlog

logger = structlog.get_logger()


class BufferManager:
    """
    Efektivní správa audio bufferu.

    Používá deque pro O(1) append místo O(n) concatenate.
    Předchází zbytečným alokacím paměti.
    """

    def __init__(self, max_size: Optional[int] = None):
        """
        Args:
            max_size: Maximální počet framů (None = unlimited)
        """
        self.buffer = deque(maxlen=max_size)
        self.max_size = max_size
        self.frame_count = 0
        self.sample_count = 0

        logger.debug(
            "buffer_manager_initialized",
            max_size=max_size if max_size else "unlimited"
        )

    def append(self, frame: np.ndarray) -> None:
        """
        Přidej frame do bufferu (O(1) operace).

        Args:
            frame: Audio frame (numpy array)
        """
        self.buffer.append(frame)
        self.frame_count += 1
        self.sample_count += len(frame)

        # Warning pokud přetečeme maxlen (deque automaticky dropne nejstarší)
        if self.max_size and len(self.buffer) == self.max_size:
            logger.warning(
                "buffer_overflow",
                max_size=self.max_size,
                message="Oldest frames are being dropped"
            )

    def to_array(self) -> np.ndarray:
        """
        Konvertuj buffer na numpy array (single concatenate operation).

        Returns:
            Concatenated numpy array
        """
        if not self.buffer:
            logger.debug("buffer_empty_returning_empty_array")
            return np.array([], dtype=np.int16)

        # Single concatenate operation (efektivní)
        array = np.concatenate(list(self.buffer))

        logger.debug(
            "buffer_converted_to_array",
            frames=len(self.buffer),
            samples=len(array),
            size_mb=round(array.nbytes / (1024 * 1024), 2)
        )

        return array

    def clear(self) -> None:
        """Vyčisti buffer a resetuj countery."""
        self.buffer.clear()
        self.frame_count = 0
        self.sample_count = 0
        logger.debug("buffer_cleared")

    def get_last_n_frames(self, n: int) -> list:
        """
        Vrať posledních N framů.

        Args:
            n: Počet framů

        Returns:
            List posledních N framů
        """
        if n >= len(self.buffer):
            return list(self.buffer)

        # Deque podporuje slicing
        return list(self.buffer)[-n:]

    def __len__(self) -> int:
        """Počet framů v bufferu."""
        return len(self.buffer)

    @property
    def is_empty(self) -> bool:
        """Je buffer prázdný?"""
        return len(self.buffer) == 0

    @property
    def is_full(self) -> bool:
        """Je buffer plný (dosáhl max_size)?"""
        if self.max_size is None:
            return False
        return len(self.buffer) >= self.max_size

    def duration_seconds(self, sample_rate: int = 16000) -> float:
        """
        Délka bufferu v sekundách.

        Args:
            sample_rate: Sample rate (Hz)

        Returns:
            Délka v sekundách
        """
        return self.sample_count / sample_rate

    def get_statistics(self) -> dict:
        """
        Vrať statistiky o bufferu.

        Returns:
            Dictionary se statistikami
        """
        return {
            'frames': len(self.buffer),
            'samples': self.sample_count,
            'max_size': self.max_size,
            'is_full': self.is_full,
            'frame_count_total': self.frame_count  # Včetně droppnutých
        }
