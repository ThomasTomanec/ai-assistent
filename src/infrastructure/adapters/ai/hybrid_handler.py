"""
Hybrid AI Handler with streaming callback propagation
Cloud-primary strategie: Rychlost + Soukromí + Offline fallback
"""

import structlog
from typing import Callable
from src.core.ports.i_command_handler import ICommandHandler
from src.infrastructure.adapters.ai.local_model_handler import (
    LocalModelHandler,
    OllamaUnavailableError
)
from src.infrastructure.adapters.ai.cloud_model_handler import (
    CloudModelHandler,
    CloudProviderUnavailableError
)
from src.core.routing.intelligent_router import IntelligentRouter, RoutingDecision
from src.core.exceptions import AIError

logger = structlog.get_logger()


class HybridAIHandler(ICommandHandler):
    """
    Hybrid handler s cloud-primary strategií a streaming support.

    Routing strategie:
    - Fáze 1: PII detection → FORCE_LOCAL (ochrana soukromí)
    - Fáze 2-4: Cloud primary (rychlost)
    - Fáze 5: Cloud fail → Local fallback (offline režim)
    """

    def __init__(self, cloud_handler: CloudModelHandler,
                 local_handler: LocalModelHandler,
                 user_preference: str = None):
        """
        Args:
            cloud_handler: Cloudový AI handler (s context builderem)
            local_handler: Lokální AI handler
            user_preference: 'local_only', 'cloud_only', nebo None (auto)
        """
        self.router = IntelligentRouter(user_preference=user_preference)
        self.local_handler = local_handler
        self.cloud_handler = cloud_handler
        self.response_callback = None
        logger.info("hybrid_ai_handler_initialized",
                   router="intelligent_5phase",
                   strategy="cloud_primary_privacy_local_fallback")

    def set_response_callback(self, callback: Callable):
        """
        Set callback for streaming response chunks.
        Propagates to underlying handlers.

        Args:
            callback: Function(chunk: str, is_final: bool)
        """
        self.response_callback = callback

        # Propagate to handlers
        if hasattr(self.cloud_handler, 'set_response_callback'):
            self.cloud_handler.set_response_callback(callback)

        if hasattr(self.local_handler, 'set_response_callback'):
            self.local_handler.set_response_callback(callback)

    def process(self, text: str, asr_confidence: float = 1.0) -> str:
        """
        Zpracuj dotaz s cloud-primary strategií.

        Strategie:
        1. PII → lokálně (FORCE_LOCAL) - žádný cloud!
        2. Ostatní → cloud (rychlost)
        3. Cloud fail → lokálně (fallback)

        Args:
            text: Přepsaný text z STT
            asr_confidence: Confidence score z ASR (0-1)

        Returns:
            Odpověď z lokálního nebo cloudového modelu
        """
        decision, metadata = self.router.route(
            text=text,
            asr_confidence=asr_confidence,
            session_context_length=0
        )

        # Clarification needed
        if decision == RoutingDecision.ASK_CLARIFICATION:
            logger.info("asking_clarification", metadata=metadata)
            return "Omlouvám se, nerozuměl jsem správně. Můžeš to prosím zopakovat?"

        # Force local (PII detected)
        if decision == RoutingDecision.FORCE_LOCAL:
            logger.info("routing_to_local_privacy",
                       reason="PII_detected",
                       metadata=metadata)

            return self._process_local_only(text)

        # Cloud-primary strategy for non-PII queries
        return self._process_cloud_with_fallback(text, metadata)

    def _process_local_only(self, text: str) -> str:
        """
        Process with local model only (PII protection).
        No cloud fallback for privacy.
        """
        try:
            response = self.local_handler.process(text)
            logger.info("local_processing_success_privacy_mode")
            return response

        except OllamaUnavailableError:
            logger.error("local_handler_unavailable_privacy_mode",
                        reason="ollama_not_running",
                        no_cloud_fallback="privacy_protection")
            return "Omlouvám se, lokální zpracování není momentálně dostupné. " \
                   "Z důvodu ochrany soukromí nemohu použít cloud. Zkus to prosím později."

        except AIError as e:
            logger.error("local_handler_failed_privacy_mode",
                        error=str(e),
                        no_cloud_fallback="privacy_protection")
            return "Omlouvám se, nastala chyba při zpracování dotazu. Zkus to prosím znovu."

    def _process_cloud_with_fallback(self, text: str, metadata: dict) -> str:
        """
        Process with cloud, fallback to local if cloud fails.
        """
        # Try cloud first
        try:
            logger.info("routing_to_cloud", metadata=metadata)
            response = self.cloud_handler.process(text)
            logger.info("cloud_processing_success")
            return response

        except CloudProviderUnavailableError:
            logger.warning("cloud_unavailable_attempting_local_fallback",
                          reason="internet_not_available")
            return self._fallback_to_local(text)

        except AIError as e:
            logger.warning("cloud_processing_failed_attempting_local_fallback",
                          error=str(e))
            return self._fallback_to_local(text)

    def _fallback_to_local(self, text: str) -> str:
        """
        Fallback to local model when cloud fails.
        """
        try:
            logger.info("attempting_local_fallback")
            response = self.local_handler.process(text)
            logger.info("local_fallback_successful")
            return response

        except OllamaUnavailableError:
            logger.error("local_fallback_unavailable",
                        reason="ollama_not_running")
            return "Omlouvám se, momentálně nejsem schopen odpovědět. " \
                   "Cloud i lokální AI jsou nedostupné. Zkus to prosím později."

        except AIError as e:
            logger.error("local_fallback_also_failed", error=str(e))
            return "Omlouvám se, momentálně nejsem schopen odpovědět. Zkus to prosím později."
