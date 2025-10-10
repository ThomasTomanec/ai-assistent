"""Wake word detection using OpenWakeWord"""
import numpy as np
import structlog
from openwakeword.model import Model
import openwakeword

logger = structlog.get_logger()

class OpenWakeWordDetector:
    """Detects wake words using OpenWakeWord"""
    
    def __init__(self, keywords: list = None, threshold: float = 0.3):
        """
        Initialize wake word detector
        
        Args:
            keywords: List of wake word names (e.g., ["alexa", "hey_jarvis"])
            threshold: Detection threshold (0.0-1.0) - LOWERED to 0.3 for better detection
        """
        self.threshold = threshold
        
        # Download models if needed
        try:
            openwakeword.utils.download_models()
            logger.info("wake_word_models_downloaded")
        except Exception as e:
            logger.warning("model_download_warning", error=str(e))
        
        # Initialize model WITHOUT Speex (not available on macOS easily)
        if keywords and len(keywords) > 0:
            logger.info("loading_specific_models", keywords=keywords)
            self.model = Model(
                wakeword_models=keywords,
                # Speex disabled for macOS compatibility
                enable_speex_noise_suppression=False,
                # VAD with lower threshold for better detection
                vad_threshold=0.3
            )
        else:
            logger.info("loading_all_models")
            self.model = Model(
                enable_speex_noise_suppression=False,
                vad_threshold=0.3
            )
        
        logger.info("wake_word_detector_initialized", 
                   keywords=keywords if keywords else "all", 
                   threshold=threshold,
                   loaded_models=list(self.model.models.keys()))
        
        print(f"\n✅ Wake word detector ready!")
        print(f"   Models loaded: {list(self.model.models.keys())}")
        print(f"   Threshold: {threshold}")
        print(f"   VAD enabled: True\n")
    
    def detect(self, audio_chunk: np.ndarray) -> bool:
        """
        Detect wake word in audio chunk
        
        Args:
            audio_chunk: Audio data (int16 format, 1280 samples for 16kHz)
            
        Returns:
            True if wake word detected, False otherwise
        """
        try:
            # OpenWakeWord expects int16 audio
            if audio_chunk.dtype != np.int16:
                audio_chunk = audio_chunk.astype(np.int16)
            
            # Flatten if needed
            if len(audio_chunk.shape) > 1:
                audio_chunk = audio_chunk.flatten()
            
            # Check chunk size (must be exactly 1280 samples for 16kHz)
            if len(audio_chunk) != 1280:
                return False
            
            # Get predictions
            predictions = self.model.predict(audio_chunk)
            
            # Log all predictions for debugging
            for wake_word, score in predictions.items():
                if score > 0.1:  # Log anything above 0.1 to see activity
                    print(f"   🎯 {wake_word}: {score:.3f}", end="\r")
                
                if score >= self.threshold:
                    print(f"\n   ✨ DETECTED! {wake_word}: {score:.3f}\n")
                    logger.info("wake_word_detected!", 
                              word=wake_word, 
                              score=float(score))
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
