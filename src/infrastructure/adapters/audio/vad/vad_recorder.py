# src/infrastructure/adapters/audio/vad/vad_recorder.py

"""
VAD Recorder - Production-ready with noise rejection and trimming.
Implements double-threshold VAD with trailing silence (LiveKit/Alexa style).
"""

import asyncio
from typing import Optional, Callable

import numpy as np
import structlog

from .models import RecordingConfig, RecordingMetrics
from .functionality import (
    ProximityDetector,
    AudioValidator,
    BufferManager,
    MetricsTracker
)

logger = structlog.get_logger()


class VADRecorder:
    """
    Production-ready VAD recorder with best practices from industry leaders.

    Features:
    - Double-threshold VAD with hysteresis (Google/Alexa style)
    - Ultra-fast trailing silence detection (0.3s)
    - RMS energy with exponential smoothing
    - Robust calibration with noise rejection
    - Post-processing silence trimming
    """

    def __init__(
            self,
            audio_input,
            stream=None,
            config: Optional[RecordingConfig] = None
    ):
        """
        Args:
            audio_input: Audio input adapter
            stream: Optional pre-existing stream
            config: Recording configuration
        """
        self.audio_input = audio_input
        self.stream = stream
        self.config = config or RecordingConfig()
        self.config.validate()

        # Functionality modules (for metrics, not used for rejection in production)
        self.proximity = ProximityDetector(
            threshold_multiplier=self.config.proximity_threshold,
            margin=self.config.proximity_margin,
            enabled=self.config.proximity_enabled
        )

        self.validator = AudioValidator(
            min_volume=self.config.min_volume_threshold,
            max_volume=self.config.max_volume_threshold,
            noise_gate_enabled=self.config.noise_gate_enabled,
            noise_gate_ratio=self.config.noise_gate_ratio
        )

        # State
        self.last_metrics: Optional[RecordingMetrics] = None
        self._is_recording = False
        self._current_tracker: Optional[MetricsTracker] = None

        # Double-threshold VAD parameters with SAFE defaults (higher for noise rejection)
        self.high_threshold = 1200.0  # Start speech (higher = less background noise)
        self.low_threshold = 600.0  # Continue speech (higher = less background noise)
        self.smoothed_energy = 0.0  # Exponential smoothing
        self.smoothing_factor = 0.25  # Smoothing rate (0.25 = stable)
        self.calibrated = False  # Calibration flag

        logger.info(
            "vad_recorder_initialized",
            config=self.config.to_dict(),
            vad_type="double_threshold_rms_with_trimming",
            default_thresholds="high=1200, low=600"
        )

    async def __aenter__(self):
        """Context manager entry."""
        if not self.stream:
            self.stream = self.audio_input.start_stream()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup."""
        if self.stream:
            try:
                self.stream.stop()
            except Exception as e:
                logger.warning("stream_stop_error", error=str(e))
        return False

    @property
    def is_recording(self) -> bool:
        """Je právě aktivní nahrávání?"""
        return self._is_recording

    def get_current_metrics(self) -> Optional[RecordingMetrics]:
        """Vrať aktuální metriky během nahrávání (real-time)."""
        if self._current_tracker:
            return self._current_tracker.get_current_metrics()
        return None

    def _calculate_rms_energy(self, frame: np.ndarray) -> float:
        """
        Calculate RMS energy (industry standard).
        Better than mean for speech detection.
        """
        if frame.dtype == np.int16:
            frame_float = frame.astype(np.float32)
        else:
            frame_float = frame

        return float(np.sqrt(np.mean(frame_float ** 2)))

    def _double_threshold_vad(
            self,
            frame: np.ndarray,
            speech_active: bool
    ) -> tuple[bool, float]:
        """
        Double-threshold VAD with hysteresis (Google/Alexa style).

        Args:
            frame: Audio frame
            speech_active: Is speech currently active?

        Returns:
            (is_speech, energy)
        """
        # Calculate RMS energy
        energy = self._calculate_rms_energy(frame)

        # Exponential smoothing for stability
        self.smoothed_energy = (
                (1 - self.smoothing_factor) * self.smoothed_energy +
                self.smoothing_factor * energy
        )

        # Double threshold logic
        if speech_active:
            # During speech - use low threshold (catch quiet parts)
            is_speech = self.smoothed_energy > self.low_threshold
        else:
            # Before speech - use high threshold (prevent false starts)
            is_speech = self.smoothed_energy > self.high_threshold

        return is_speech, self.smoothed_energy

    def _trim_silence(self, audio: np.ndarray, threshold: float = 500.0) -> np.ndarray:
        """
        Odstřihni ticho ze začátku a konce nahrávky.
        Pomáhá proti background noise v nahrávce.

        Args:
            audio: Audio array
            threshold: Energy threshold for speech detection

        Returns:
            Trimmed audio array
        """
        if len(audio) == 0:
            return audio

        # Frame size
        frame_size = self.config.frame_size

        # Najdi první speech frame (od začátku)
        start_idx = 0
        for i in range(0, len(audio) - frame_size, frame_size):
            frame = audio[i:i + frame_size]
            energy = float(np.sqrt(np.mean(frame.astype(np.float32) ** 2)))
            if energy > threshold:
                start_idx = max(0, i - frame_size * 2)  # Keep 2 frames before
                break

        # Najdi poslední speech frame (od konce)
        end_idx = len(audio)
        for i in range(len(audio) - frame_size, 0, -frame_size):
            if i + frame_size > len(audio):
                continue
            frame = audio[i:i + frame_size]
            energy = float(np.sqrt(np.mean(frame.astype(np.float32) ** 2)))
            if energy > threshold:
                end_idx = min(len(audio), i + frame_size * 3)  # Keep 3 frames after
                break

        # Ensure we have valid indices
        if start_idx >= end_idx or start_idx >= len(audio):
            return audio

        return audio[start_idx:end_idx]

    async def _read_frame(self) -> np.ndarray:
        """Helper metoda pro čtení framu."""
        if not self.stream:
            raise RuntimeError("Stream not initialized")

        return await self.audio_input.read_chunk(self.stream)

    async def calibrate_background(
            self,
            duration: float = 2.0,
            auto_adjust: bool = True
    ) -> float:
        """
        Kalibruj background noise a VAD thresholdy.
        ROBUST: Always works, even in noisy environments.
        HIGHER THRESHOLDS: Better noise rejection.

        Args:
            duration: Calibration duration (seconds)
            auto_adjust: Auto-adjust thresholds for environment

        Returns:
            Mean background energy
        """
        logger.info("calibrating_background", duration=duration, auto_adjust=auto_adjust)

        if not self.stream:
            self.stream = self.audio_input.start_stream()

        energies = []
        frames_to_read = int(duration * 1000 / self.config.frame_duration_ms)

        for _ in range(frames_to_read):
            try:
                frame = await self._read_frame()
                energy = self._calculate_rms_energy(frame)
                energies.append(energy)
                await asyncio.sleep(0)
            except Exception as e:
                logger.warning("calibration_frame_error", error=str(e))
                continue

        if not energies:
            logger.warning("calibration_failed_no_samples", using_defaults=True)
            return 0.0

        # Calculate statistics
        mean_energy = float(np.mean(energies))
        std_energy = float(np.std(energies))
        median_energy = float(np.median(energies))

        # Detect noisy environment
        is_noisy = mean_energy > 500 or std_energy > 300

        if is_noisy:
            logger.warning(
                "noisy_environment_detected",
                mean_energy=round(mean_energy, 1),
                std_energy=round(std_energy, 1),
                recommendation="Using higher thresholds for noise rejection"
            )

        # Set thresholds - HIGHER for better noise rejection
        if auto_adjust:
            if is_noisy:
                # Noisy environment - use high conservative thresholds
                self.high_threshold = max(1200.0, median_energy + 2.5 * std_energy)
                self.low_threshold = max(600.0, median_energy + 1.5 * std_energy)
            else:
                # Quiet environment - still use higher thresholds than before
                self.high_threshold = max(1000.0, mean_energy + 3.0 * std_energy)
                self.low_threshold = max(500.0, mean_energy + 1.5 * std_energy)
        else:
            # Manual mode - use safe high defaults
            self.high_threshold = 1200.0
            self.low_threshold = 600.0

        # Initialize smoothed energy
        self.smoothed_energy = mean_energy
        self.calibrated = True

        # Calibrate modules for metrics (use median for robustness)
        background_volume = median_energy
        self.proximity.calibrate(background_volume)
        self.validator.set_background_noise(background_volume)

        logger.info(
            "background_calibrated",
            mean_energy=round(mean_energy, 1),
            median_energy=round(median_energy, 1),
            std_energy=round(std_energy, 1),
            high_threshold=round(self.high_threshold, 1),
            low_threshold=round(self.low_threshold, 1),
            is_noisy=is_noisy,
            samples_count=len(energies)
        )

        return mean_energy

    async def record_until_silence(
            self,
            max_duration: Optional[float] = None,
            silence_duration: Optional[float] = None,
            on_progress: Optional[Callable[[RecordingMetrics], None]] = None
    ) -> tuple[np.ndarray, RecordingMetrics]:
        """
        Nahrává audio dokud nedetekuje ticho - ULTRA-FAST with trimming.

        Uses ultra-fast trailing silence detection:
        - Initial silence: 1.0s (prevent false starts)
        - Trailing silence: 0.3s (ultra-fast response)
        - Post-processing: Trim silence from start/end
        """
        # Initialize modules
        buffer = BufferManager(max_size=self.config.max_frames)
        tracker = MetricsTracker()
        self._current_tracker = tracker
        self._is_recording = True

        # Config
        max_dur = max_duration or self.config.max_duration

        # ULTRA-FAST adaptive silence thresholds
        trailing_silence_frames = 10  # 0.3s @ 30ms frames (ultra-fast!)
        initial_silence_frames = 33  # 1.0s @ 30ms frames (prevent false starts)

        # Start stream if needed
        if not self.stream:
            self.stream = self.audio_input.start_stream()

        # Recording state
        silence_frames = 0
        speech_frames = 0
        speech_started = False
        stop_reason = "unknown"

        # Progress callback state
        last_progress_update = 0
        progress_interval = 0.5  # 500ms

        logger.info(
            "recording_started",
            max_duration=max_dur,
            trailing_silence="0.3s",
            initial_silence="1.0s",
            high_threshold=round(self.high_threshold, 1),
            low_threshold=round(self.low_threshold, 1),
            calibrated=self.calibrated
        )

        try:
            while True:
                # Check max duration
                elapsed = tracker.metrics.duration_seconds
                if elapsed >= max_dur:
                    stop_reason = "max_duration"
                    logger.info("max_duration_reached", duration=elapsed)
                    break

                # Progress callback
                if on_progress and (elapsed - last_progress_update) >= progress_interval:
                    try:
                        on_progress(tracker.get_current_metrics())
                        last_progress_update = elapsed
                    except Exception as e:
                        logger.warning("progress_callback_error", error=str(e))

                # Read frame
                try:
                    frame = await self._read_frame()
                except Exception as e:
                    logger.error("frame_read_error", error=str(e))
                    stop_reason = "error"
                    break

                # Extract volume for metrics
                volume = float(np.abs(frame).mean())

                # Double-threshold VAD (the core logic)
                is_speech, energy = self._double_threshold_vad(frame, speech_started)

                # Update metrics (forced OK for production)
                proximity_ok = True
                quality_ok = True
                tracker.update_frame(is_speech, volume, proximity_ok, quality_ok)

                # Decision logic
                if is_speech:
                    # Speech detected
                    buffer.append(frame)
                    silence_frames = 0
                    speech_frames += 1

                    if speech_frames >= self.config.min_speech_frames:
                        speech_started = True
                else:
                    # Silence detected
                    buffer.append(frame)  # Keep for smooth audio
                    silence_frames += 1

                # Adaptive silence threshold (trailing vs initial)
                if speech_started:
                    required_silence = trailing_silence_frames  # Ultra-fast: 0.3s
                else:
                    required_silence = initial_silence_frames  # Slow: 1.0s

                # Check stop condition
                if speech_started and silence_frames >= required_silence:
                    stop_reason = "silence"
                    logger.info(
                        "silence_detected",
                        silence_frames=silence_frames,
                        speech_frames=speech_frames,
                        duration=elapsed,
                        silence_type="trailing"
                    )
                    break

                # Yield to event loop
                await asyncio.sleep(0)

        finally:
            # Finalize metrics
            tracker.set_sample_count(buffer.sample_count)
            metrics = tracker.finalize(stop_reason)
            metrics.background_noise = self.proximity.background_noise

            # Store for later access
            self.last_metrics = metrics
            self._current_tracker = None
            self._is_recording = False

            # Log summary
            logger.info("recording_finished", **metrics.to_dict())

        # Convert buffer to array
        audio_array = buffer.to_array()

        # Post-processing: Trim silence from start and end (removes background noise)
        original_length = len(audio_array)
        if len(audio_array) > 0:
            audio_array = self._trim_silence(audio_array, threshold=self.low_threshold)
            trimmed_length = len(audio_array)
            if trimmed_length < original_length:
                logger.debug(
                    "audio_trimmed",
                    original_samples=original_length,
                    trimmed_samples=trimmed_length,
                    removed_samples=original_length - trimmed_length
                )

        return audio_array, metrics

    def get_last_metrics(self) -> Optional[RecordingMetrics]:
        """Vrátí metriky z posledního nahrávání."""
        return self.last_metrics

    def reset_calibration(self) -> None:
        """Resetuj kalibraci."""
        self.proximity.reset_calibration()
        self.validator.set_background_noise(0.0)
        self.high_threshold = 1200.0
        self.low_threshold = 600.0
        self.smoothed_energy = 0.0
        self.calibrated = False
        logger.info("calibration_reset")

    def get_statistics(self) -> dict:
        """Vrať celkové statistiky recorderu."""
        return {
            'config': self.config.to_dict(),
            'calibrated': self.calibrated,
            'high_threshold': round(self.high_threshold, 1),
            'low_threshold': round(self.low_threshold, 1),
            'smoothed_energy': round(self.smoothed_energy, 1),
            'is_recording': self.is_recording,
            'vad_type': 'double_threshold_rms_with_trimming',
            'last_recording': self.last_metrics.to_dict() if self.last_metrics else None
        }
