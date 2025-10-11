import aiohttp
import asyncio
from src.core.ports.i_command_handler import ICommandHandler
import structlog
import os

logger = structlog.get_logger()

class LocalCommandHandler(ICommandHandler):
    def process(self, text: str) -> str:
        # Můžeš doplnit víc příkazů
        text_lower = text.lower()
        if any(k in text_lower for k in ['počasí', 'teplota', 'weather']):
            return "Venku je asi 15°C a polojasno. (lokální odpověď)"
        if any(k in text_lower for k in ['čas', 'time', 'kolik je']):
            from datetime import datetime
            now = datetime.now()
            return f"Je {now.hour}:{now.minute:02d}."
        if any(k in text_lower for k in ['ahoj', 'hello', 'nazdar']):
            return "Ahoj! Jak ti mohu pomoci?"
        return ""

class CloudCommandHandler(ICommandHandler):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.openai.com/v1/chat/completions"  # Příklad OpenAI API

    async def process_async(self, text: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        json_payload = {
            "model": "gpt-4-turbo",
            "messages": [{"role": "user", "content": text}]
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(self.api_url, headers=headers, json=json_payload) as resp:
                if resp.status != 200:
                    logger.error(f"Cloud API error: {resp.status}")
                    return "Promiň, nemohu teď zpracovat složitější dotazy."
                data = await resp.json()
                return data["choices"][0]["message"]['content'].strip()

class HybridCommandHandler(ICommandHandler):
    def __init__(self, local_handler: LocalCommandHandler, cloud_handler: CloudCommandHandler):
        self.local_handler = local_handler
        self.cloud_handler = cloud_handler

    def is_simple_command(self, text: str) -> bool:
        # Jednoduché rozhodnutí podle délky a klíčových slov
        keywords = ['počasí', 'čas', 'ahoj', 'pomoc', 'teplota', 'kolik']
        if len(text.split()) <= 7 and any(k in text.lower() for k in keywords):
            return True
        return False

    def process(self, text: str) -> str:
        if self.is_simple_command(text):
            response = self.local_handler.process(text)
            if response:
                return response
        # Asynchronně voláme cloud, tady synchronní výzva není snadná, doporučuji běh v asyncio smyčce
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.cloud_handler.process_async(text))
