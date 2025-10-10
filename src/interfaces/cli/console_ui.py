"""CLI user interface for voice assistant"""

import asyncio
import structlog
from src.application.services.assistant_orchestrator import AssistantOrchestrator

logger = structlog.get_logger()

class ConsoleUI:
    """Command-line interface with all print/UI logic"""
    
    def __init__(self, orchestrator: AssistantOrchestrator):
        self.orchestrator = orchestrator
        logger.info("console_ui_initialized")
    
    async def run(self):
        """Main UI loop"""
        self._print_header()
        
        await self.orchestrator.start()
        
        try:
            while True:
                await self._interaction_loop()
        except KeyboardInterrupt:
            await self.orchestrator.stop()
            raise
    
    def _print_header(self):
        """Print application header"""
        print("\n" + "="*60)
        print("🎤 VOICE MODE - Say 'Alexa' to activate")
        print("="*60 + "\n")
    
    async def _interaction_loop(self):
        """Single interaction cycle with user"""
        # 1. Listen for wake word
        print("👂 Listening for wake word...")
        detected = await self.orchestrator.wait_for_wake_word()
        
        if not detected:
            return
        
        # 2. Wake word detected
        print("\n✨ Wake word detected!")
        print("💬 Say your command now (5 seconds)...\n")
        
        # 3. Capture command
        print("🔄 Processing your command...\n")
        command_text = await self.orchestrator.capture_command()
        
        # 4. Validate command
        if not command_text or len(command_text.strip()) == 0:
            print("❌ No command detected\n")
            print("-"*60 + "\n")
            await asyncio.sleep(2)
            return
        
        # 5. Show what was heard
        print(f"📝 You said: \"{command_text}\"")
        print(f"⏱️  Processing...\n")
        
        # 6. Process command
        response = self.orchestrator.process_command(command_text)
        
        # 7. Show response
        print(f"🤖 Bot: {response}\n")
        print("-"*60 + "\n")
        
        # 8. Cooldown to prevent false triggers
        await asyncio.sleep(2)
