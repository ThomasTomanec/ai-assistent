"""
Context Builder - Sestavuje kontext pro AI modely
"""

import structlog
from typing import Optional
from src.core.config.user_config import UserConfig  # <-- OPRAVENO
from src.application.services.time_service import TimeService

logger = structlog.get_logger()

class ContextBuilder:
    """Sestavuje kompletní kontext pro AI system prompt"""

    def __init__(self, user_config: UserConfig, time_service: TimeService):
        """
        Args:
            user_config: Uživatelská konfigurace
            time_service: Služba pro práci s časem
        """
        self.user_config = user_config
        self.time_service = time_service
        logger.info("context_builder_initialized")

    def build_system_prompt(self, include_time: bool = True,
                           include_user_info: bool = True) -> str:
        """
        Sestav kompletní system prompt.

        Args:
            include_time: Zahrnout časové informace
            include_user_info: Zahrnout informace o uživateli

        Returns:
            Kompletní system prompt
        """
        parts = ["Jsi inteligentní hlasový asistent."]

        # Uživatelský kontext
        if include_user_info:
            user_context = self._build_user_context()
            if user_context:
                parts.append(user_context)

        # Časový kontext
        if include_time:
            time_context = self._build_time_context()
            if time_context:
                parts.append(time_context)

        # Instrukce pro odpovídání
        parts.append(self._build_response_instructions())

        return "\n\n".join(parts)

    def _build_user_context(self) -> str:
        """Sestaví kontext o uživateli"""
        user_name = self.user_config.get('user.name')
        city = self.user_config.get('location.city')
        occupation = self.user_config.get('personal.occupation')
        interests = self.user_config.get('personal.interests', [])

        parts = []

        if user_name and user_name != 'User':
            parts.append(f"Mluvíš s uživatelem jménem {user_name}.")

        if city and city != 'Unknown':
            country = self.user_config.get('location.country', '')
            if country:
                parts.append(f"Uživatel je z města {city}, {country}.")
            else:
                parts.append(f"Uživatel je z města {city}.")

        if occupation:
            parts.append(f"Pracuje jako {occupation}.")

        if interests:
            interests_str = ", ".join(interests)
            parts.append(f"Zajímá se o: {interests_str}.")

        return " ".join(parts) if parts else ""

    def _build_time_context(self) -> str:
        """Sestaví časový kontext"""
        time_info = self.time_service.get_time_context()

        return f"""Aktuální datum a čas: {time_info['formatted']}
Časová zóna: {time_info['timezone']}

Pokud se uživatel ptá na čas, datum nebo den v týdnu, odpověz na základě těchto informací."""

    def _build_response_instructions(self) -> str:
        """Sestaví instrukce pro styl odpovědí"""
        personality = self.user_config.get('assistant.personality', 'přátelský')
        response_style = self.user_config.get('assistant.response_style', 'stručný')

        return f"""Tvůj styl komunikace: {personality} a {response_style}.
Odpovídej přirozeně v češtině.
Při odpovědích o času používej 24hodinový formát."""

    def get_quick_time_answer(self, query: str) -> Optional[str]:
        """
        Poskytne rychlou odpověď na jednoduché časové dotazy bez volání AI.

        Args:
            query: Dotaz uživatele (lowercase)

        Returns:
            Odpověď nebo None, pokud není jednoduchý časový dotaz
        """
        query_lower = query.lower()
        time_info = self.time_service.get_time_context()

        # Kolik je hodin?
        if any(phrase in query_lower for phrase in ['kolik je hodin', 'kolik máme hodin', 'kolik je teď']):
            return f"Je {time_info['hour']}:{time_info['minute']}."

        # Jaký je den?
        if any(phrase in query_lower for phrase in ['jaký je den', 'jaký máme den', 'který je den']):
            return f"Dnes je {time_info['day_name']}."

        # Jaké je datum?
        if any(phrase in query_lower for phrase in ['jaké je datum', 'jaké máme datum', 'které máme datum']):
            return f"Dnes je {time_info['day']}. {time_info['month_name']} {time_info['year']}."

        return None
