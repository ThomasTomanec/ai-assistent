"""CLI user interface with streaming support"""

import asyncio
import sys
import structlog

logger = structlog.get_logger()

class ConsoleUI:
    """Clean command-line interface with streaming support"""

    def __init__(self, orchestrator, user_config):
        self.orchestrator = orchestrator
        self.user_config = user_config
        self.wake_word_name = user_config.get('assistant.wake_word', 'Alexa')
        self.assistant_name = user_config.get('assistant.name', 'Alexa')
        logger.info("console_ui_initialized", wake_word=self.wake_word_name)

    async def run(self):
        """Main UI loop"""
        self._print_header()

        # Set streaming callback
        self.orchestrator.set_response_callback(self._on_response_chunk)

        await self.orchestrator.start()

        try:
            while True:
                await self._interaction_loop()
        except KeyboardInterrupt:
            await self.orchestrator.stop()
            raise

    def _print_header(self):
        """Print header"""
        user_name = self.user_config.get('user.name', 'User')

        print("\n" + "═"*60)
        print("  🎤  Voice Assistant".center(60))
        print("═"*60)
        print(f"\n  👋 Hi {user_name}!")
        print(f"  💡 Say '{self.wake_word_name}' to activate")
        print("  🔇 Press Ctrl+C to exit\n")
        print("═"*60 + "\n")

    def _on_response_chunk(self, chunk: str, is_final: bool = False):
        """
        Callback for streaming response chunks.

        Args:
            chunk: Text chunk to display
            is_final: True if this is the last chunk
        """
        if chunk:
            print(chunk, end="", flush=True)

        if is_final:
            print()  # Newline at end

    async def _interaction_loop(self):
        """Interaction cycle - CLEAR FLOW with streaming"""

        # 1. WAITING FOR WAKE WORD
        print(f"💤  Say '{self.wake_word_name}' to activate...")
        detected = await self.orchestrator.wait_for_wake_word()

        if not detected:
            return

        # 2. WAKE WORD DETECTED - WAITING FOR COMMAND
        print(f"\n✨ {self.wake_word_name} activated!")
        print("🎙️ Listening for command...\n")

        # 3. CAPTURE COMMAND
        command_text = await self.orchestrator.capture_command()

        # 4. VALIDATE
        if not command_text or len(command_text.strip()) == 0:
            print("❌ No speech detected\n")
            print("─"*60 + "\n")
            await asyncio.sleep(1)
            return

        # 5. SHOW USER INPUT
        print(f"👤 You: {command_text}")

        # 6. PROCESS & SHOW RESPONSE (streaming!)
        try:
            # Print assistant prefix
            print(f"🤖 {self.assistant_name}: ", end="", flush=True)

            # Process (streaming callback will print chunks)
            response = self.orchestrator.process_command(command_text)

            # Response already printed via callback
            print("\n" + "─"*60 + "\n")

        except Exception as e:
            print(f"\n❌ Error: {str(e)}\n")
            print("─"*60 + "\n")
            logger.error("command_error", error=str(e), exc_info=True)

        # 7. COOLDOWN
        self.orchestrator.wake_word.set_speech_cooldown()
        await asyncio.sleep(0.5)
