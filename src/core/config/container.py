"""
Dependency Injection Container
"""

import structlog
import os
from src.core.config.user_config import get_user_config
from src.application.services.time_service import TimeService
from src.application.services.context_builder import ContextBuilder
from src.infrastructure.adapters.ai.cloud_model_handler import CloudModelHandler
from src.infrastructure.adapters.ai.local_model_handler import LocalModelHandler
from src.infrastructure.adapters.ai.hybrid_handler import HybridAIHandler

logger = structlog.get_logger()

def setup_container():
    """
    Sestaví všechny dependencies a vrátí hybrid handler.

    Returns:
        HybridAIHandler: Plně nakonfigurovaný handler
    """
    logger.info("setting_up_container")

    # 1. Načti user config
    user_config = get_user_config()

    # 2. Vytvoř time service s timezone z konfigurace
    timezone = user_config.get('location.timezone', 'Europe/Prague')
    time_service = TimeService(timezone=timezone)

    # 3. Vytvoř context builder
    context_builder = ContextBuilder(user_config, time_service)

    # 4. Vytvoř cloud handler s context builderem
    cloud_handler = CloudModelHandler(
        context_builder=context_builder,
        api_key=os.getenv("OPENAI_API_KEY"),
        streaming=True
    )

    # 5. Vytvoř local handler
    local_handler = LocalModelHandler()

    # 6. Vytvoř hybrid handler
    hybrid_handler = HybridAIHandler(
        cloud_handler=cloud_handler,
        local_handler=local_handler,
        user_preference=None  # Auto routing
    )

    logger.info("container_setup_complete")
    return hybrid_handler
