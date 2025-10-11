"""OpenWakeWord adapter with VAD"""

import numpy as np
import structlog
import time
from openwakeword.model import Model
import openwakeword
from src.core.ports.i_wake_word_detector import IWakeWordDetector

logger = structlog.get_logger()

class OpenWakeWordAdapter(IWakeWordDetector):
    """Wake word detector using OpenWakeWord library"""
    
    def __init__(self, keywords: list = None, threshold: float = 0.3):
        """
        Initialize OpenWakeWord detector
        
        Args:
            keywords: List of wake word names
            threshold: Detection threshold (0.0-1.0)
        """
        self.threshold = threshold
        self.last_detection_time = 0
        self.min_detection_interval = 2.0
        self.speech_cooldown_time = 0
        self.speech_cooldown_duration = 1.5

        # Download models if needed
        try:
            openwakeword.utils.download_models()
            logger.info("wake_word_models_downloaded")
        except Exception as e:
            logger.warning("model_download_warning", error=str(e))

        # Initialize model
        if keywords and len(keywords) > 0:
            logger.info("loading_specific_models", keywords=keywords)
            self.model = Model(
                wakeword_models=keywords,
                enable_speex_noise_suppression=False,
                vad_threshold=0.5
            )
        else:
            logger.info("loading_all_models")
            self.model = Model(
                enable_speex_noise_suppression=False,
                vad_threshold=0.5
            )

        logger.info(
            "openwakeword_initialized",
            keywords=keywords if keywords else "all",
            threshold=threshold,
            loaded_models=list(self.model.models.keys())
        )

        print(f"\n✅ Wake word detector ready!")
        print(f"   Models loaded: {list(self.model.models.keys())}")
        print(f"   Threshold: {threshold}")
        print(f"   VAD enabled: True\n")

    def set_speech_cooldown(self):
        """Set cooldown after bot speech to prevent echo detection"""
        self.speech_cooldown_time = time.time()
        logger.debug("speech_cooldown_set")

    def detect(self, audio_chunk: np.ndarray) -> bool:
        """
        Detect wake word in audio chunk

        Args:
            audio_chunk: Audio data (int16 format, 1280 samples)

        Returns:
            True if wake word detected, False otherwise
        """
        try:
            current_time = time.time()

            # Check speech cooldown (after bot response)
            if current_time - self.speech_cooldown_time < self.speech_cooldown_duration:
                return False

            # Anti-spam - ignore too frequent detections
            if current_time - self.last_detection_time < self.min_detection_interval:
                return False

            # OpenWakeWord expects int16 audio
            if audio_chunk.dtype != np.int16:
                audio_chunk = audio_chunk.astype(np.int16)

            # Flatten if needed
            if len(audio_chunk.shape) > 1:
                audio_chunk = audio_chunk.flatten()

            # Check chunk size
            if len(audio_chunk) != 1280:
                return False

            # Get predictions
            predictions = self.model.predict(audio_chunk)

            # Check for wake word detection
            for wake_word, score in predictions.items():
                if score >= self.threshold:
                    logger.info(
                        "wake_word_detected!", 
                        word=wake_word, 
                        score=float(score)
                    )
                    self.last_detection_time = current_time
                    return True
            
            return False
            
        except Exception as e:
            logger.error("detection_error", error=str(e), exc_info=True)
            return False
    
    def reset(self):
        """Reset the detector state"""
        try:
            self.model.reset()
            logger.debug("detector_reset")
        except Exception as e:
            logger.error("reset_error", error=str(e))
