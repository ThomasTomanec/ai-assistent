"""
Time Service - Správa času s ohledem na timezone
"""

import structlog
from datetime import datetime
from typing import Dict

# Podpora pro Python 3.9+
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

logger = structlog.get_logger()

class TimeService:
    """Služba pro práci s časem podle timezone"""

    def __init__(self, timezone: str = "Europe/Prague"):
        """
        Args:
            timezone: IANA timezone string (např. "Europe/Prague", "America/New_York")
        """
        try:
            self.timezone = ZoneInfo(timezone)
            self.timezone_name = timezone
            logger.info("time_service_initialized", timezone=timezone)
        except Exception as e:
            logger.error("invalid_timezone", timezone=timezone, error=str(e))
            # Fallback na UTC
            self.timezone = ZoneInfo("UTC")
            self.timezone_name = "UTC"

    def get_current_datetime(self) -> datetime:
        """
        Získej aktuální čas v nastaveném timezone.

        Returns:
            Timezone-aware datetime object
        """
        return datetime.now(self.timezone)

    def get_formatted_datetime(self) -> str:
        """
        Získej formátovaný datum a čas v češtině.

        Returns:
            Formátovaný string (např. "Sobota, 11. 10. 2025, 22:49")
        """
        now = self.get_current_datetime()

        day_names = ['Pondělí', 'Úterý', 'Středa', 'Čtvrtek', 'Pátek', 'Sobota', 'Neděle']
        day_name = day_names[now.weekday()]

        return f"{day_name}, {now.day}. {now.month}. {now.year}, {now.hour:02d}:{now.minute:02d}"

    def get_time_context(self) -> Dict[str, str]:
        """
        Získej slovník s časovými informacemi.

        Returns:
            Slovník s časovými údaji
        """
        now = self.get_current_datetime()

        day_names = ['Pondělí', 'Úterý', 'Středa', 'Čtvrtek', 'Pátek', 'Sobota', 'Neděle']
        month_names = [
            'ledna', 'února', 'března', 'dubna', 'května', 'června',
            'července', 'srpna', 'září', 'října', 'listopadu', 'prosince'
        ]

        return {
            'formatted': self.get_formatted_datetime(),
            'day_name': day_names[now.weekday()],
            'day': str(now.day),
            'month': str(now.month),
            'month_name': month_names[now.month - 1],
            'year': str(now.year),
            'hour': f"{now.hour:02d}",
            'minute': f"{now.minute:02d}",
            'timezone': self.timezone_name
        }
