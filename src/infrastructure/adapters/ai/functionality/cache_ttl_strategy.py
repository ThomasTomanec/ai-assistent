# src/infrastructure/adapters/ai/functionality/cache_ttl_strategy.py

"""Smart TTL strategy for AI response caching"""

import re
from typing import Optional


class CacheTTLStrategy:
    """
    Determines appropriate TTL based on query content.
    """

    # Time-sensitive keywords (short TTL)
    TIME_KEYWORDS = [
        'čas', 'hodin', 'času', 'hodina', 'time', 'clock',
        'teď', 'nyní', 'now', 'aktuální', 'current'
    ]

    # Weather keywords (medium TTL)
    WEATHER_KEYWORDS = [
        'počasí', 'weather', 'teplota', 'temperature',
        'prší', 'rain', 'sněží', 'snow', 'slunce', 'sun'
    ]

    # Date/day keywords (medium TTL)
    DATE_KEYWORDS = [
        'dnes', 'today', 'zítra', 'tomorrow', 'včera', 'yesterday',
        'kdy', 'when', 'datum', 'date'
    ]

    # Factual keywords (long TTL)
    FACTUAL_KEYWORDS = [
        'kdo', 'who', 'co je', 'what is', 'jak se', 'how',
        'proč', 'why', 'kde je', 'where',
        'napsal', 'wrote', 'objevil', 'discovered',
        'hlavní město', 'capital'
    ]

    # Math/calculation patterns (infinite TTL)
    MATH_PATTERN = re.compile(r'\d+\s*[\+\-\*\/]\s*\d+')

    @classmethod
    def get_ttl(cls, query: str) -> float:
        """
        Determine TTL in seconds based on query content.

        Args:
            query: User query text

        Returns:
            TTL in seconds (0 = no cache, inf = forever)
        """
        query_lower = query.lower().strip()

        # 1. Math/calculations - cache forever
        if cls.MATH_PATTERN.search(query_lower):
            return float('inf')

        # 2. Time-sensitive queries - very short TTL
        if any(keyword in query_lower for keyword in cls.TIME_KEYWORDS):
            return 30.0  # 30 seconds

        # 3. Weather queries - medium TTL
        if any(keyword in query_lower for keyword in cls.WEATHER_KEYWORDS):
            return 1800.0  # 30 minutes

        # 4. Date/day queries - short TTL
        if any(keyword in query_lower for keyword in cls.DATE_KEYWORDS):
            return 300.0  # 5 minutes

        # 5. Factual queries - long TTL
        if any(keyword in query_lower for keyword in cls.FACTUAL_KEYWORDS):
            return 3600.0  # 1 hour

        # 6. Questions that look factual - long TTL
        if '?' in query and len(query) > 10:
            return 1800.0  # 30 minutes (conservative)

        # 7. Default: don't cache (conversations, context-dependent)
        return 0.0

    @classmethod
    def should_cache(cls, query: str) -> bool:
        """Check if query should be cached at all."""
        ttl = cls.get_ttl(query)
        return ttl > 0
