"""Voice Assistant - Entry Point"""

import asyncio
import os
from src.core.logging.logger import setup_production_logging, setup_dev_logging
from src.core.config.container import setup_container

# Načti mode z env (default: production)
DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"

# Setup logging PŘED vším ostatním
if DEV_MODE:
    setup_dev_logging()
else:
    setup_production_logging()

async def main():
    """Application entry point"""
    container = setup_container()
    ui = container.console_ui()
    await ui.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!\n")
