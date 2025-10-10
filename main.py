"""Voice Assistant - Entry Point"""

import asyncio
from src.core.config.container import setup_container
from src.interfaces.cli.console_ui import ConsoleUI

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
