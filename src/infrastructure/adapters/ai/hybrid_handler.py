"""
Hybrid AI Handler s inteligentním 5-fázovým routerem
Cloud-primary strategie: Rychlost + Soukromí + Offline fallback
"""

import structlog
from src.core.ports.i_command_handler import ICommandHandler
from src.infrastructure.adapters.ai.local_model_handler import LocalModelHandler
from src.infrastructure.adapters.ai.cloud_model_handler import CloudModelHandler
from src.core.routing.intelligent_router import IntelligentRouter, RoutingDecision

logger = structlog.get_logger()

class HybridAIHandler(ICommandHandler):
    """
    Hybrid handler s cloud-primary strategií.

    Routing strategie:
    - Fáze 1: PII detection → FORCE_LOCAL (ochrana soukromí)
    - Fáze 2-4: Cloud primary (rychlost)
    - Fáze 5: Cloud fail → Local fallback (offline režim)
    """

    def __init__(self, api_key: str = None, user_preference: str = None):
        """
        Args:
            api_key: OpenAI API klíč pro cloud
            user_preference: 'local_only', 'cloud_only', nebo None (auto)
        """
        self.router = IntelligentRouter(user_preference=user_preference)
        self.local_handler = LocalModelHandler()
        self.cloud_handler = CloudModelHandler(api_key=api_key, streaming=True)
        logger.info("hybrid_ai_handler_initialized",
                   router="intelligent_5phase",
                   strategy="cloud_primary_privacy_local_fallback")

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

        if decision == RoutingDecision.ASK_CLARIFICATION:
            logger.info("asking_clarification", metadata=metadata)
            return "Omlouvám se, nerozuměl jsem správně. Můžeš to prosím zopakovat?"

        if decision == RoutingDecision.FORCE_LOCAL:
            logger.info("routing_to_local_privacy",
                       reason="PII_detected",
                       metadata=metadata)

            response = self.local_handler.process(text)

            if response.startswith("Error") or response.startswith("error"):
                logger.error("local_handler_failed_privacy_mode",
                            reason="error_response",
                            no_cloud_fallback="privacy_protection")
                return "Omlouvám se, nastala chyba při zpracování dotazu. Zkus to prosím znovu."

            return response

        # Cloud-primary strategie pro non-PII queries
        try:
            logger.info("routing_to_cloud",
                       decision=decision.value,
                       metadata=metadata)
            response = self.cloud_handler.process(text)
            return response

        except Exception as e:
            logger.warning("cloud_failed_attempting_local_fallback",
                          error=str(e),
                          fallback_strategy="local")

            try:
                response = self.local_handler.process(text)

                if response.startswith("Error") or response.startswith("error"):
                    logger.error("local_fallback_also_failed",
                                reason="error_response")
                    return "Omlouvám se, momentálně nejsem schopen odpovědět. Zkus to prosím později."

                logger.info("local_fallback_successful")
                return response

            except Exception as local_error:
                logger.error("local_fallback_exception",
                            error=str(local_error))
                return "Omlouvám se, momentálně nejsem schopen odpovědět. Zkus to prosím později."
