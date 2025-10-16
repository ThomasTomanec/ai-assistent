# src/infrastructure/adapters/ai/functionality/response_cache.py

"""Smart response cache with TTL and LRU eviction"""

import time
import hashlib
from typing import Optional, Dict
from collections import OrderedDict
import structlog

from .cache_ttl_strategy import CacheTTLStrategy

logger = structlog.get_logger()


class CacheEntry:
    """Single cache entry with TTL"""

    def __init__(self, response: str, ttl: float):
        self.response = response
        self.created_at = time.time()
        self.ttl = ttl
        self.hits = 0

    def is_expired(self) -> bool:
        """Check if entry is expired"""
        if self.ttl == float('inf'):
            return False
        return (time.time() - self.created_at) > self.ttl

    def get_age(self) -> float:
        """Get age in seconds"""
        return time.time() - self.created_at


class ResponseCache:
    """
    Smart LRU cache for AI responses with:
    - TTL based on query type
    - LRU eviction
    - Hit rate tracking
    """

    def __init__(self, max_size: int = 100, enabled: bool = True):
        """
        Args:
            max_size: Maximum cache entries
            enabled: Enable/disable cache
        """
        self.max_size = max_size
        self.enabled = enabled
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()

        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0

        logger.info("response_cache_initialized",
                    max_size=max_size, enabled=enabled)

    def _hash_query(self, query: str) -> str:
        """Create hash of query (case-insensitive, normalized)"""
        normalized = query.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()

    def get(self, query: str) -> Optional[str]:
        """
        Get cached response if available and not expired.

        Args:
            query: User query

        Returns:
            Cached response or None
        """
        if not self.enabled:
            return None

        key = self._hash_query(query)

        if key not in self.cache:
            self.misses += 1
            logger.debug("cache_miss", query=query[:50])
            return None

        entry = self.cache[key]

        # Check expiration
        if entry.is_expired():
            logger.debug("cache_expired", query=query[:50],
                         age=round(entry.get_age(), 1))
            del self.cache[key]
            self.misses += 1
            return None

        # Move to end (LRU)
        self.cache.move_to_end(key)
        entry.hits += 1
        self.hits += 1

        logger.info("cache_hit", query=query[:50],
                    age=round(entry.get_age(), 1),
                    total_hits=entry.hits)

        return entry.response

    def set(self, query: str, response: str) -> None:
        """
        Cache response with smart TTL.

        Args:
            query: User query
            response: AI response
        """
        if not self.enabled:
            return

        # Determine TTL
        ttl = CacheTTLStrategy.get_ttl(query)

        if ttl == 0:
            logger.debug("cache_skip", query=query[:50], reason="ttl=0")
            return

        key = self._hash_query(query)

        # Evict oldest if full
        if len(self.cache) >= self.max_size and key not in self.cache:
            self._evict_oldest()

        # Store entry
        self.cache[key] = CacheEntry(response, ttl)
        self.cache.move_to_end(key)

        logger.info("cache_set", query=query[:50],
                    ttl=ttl if ttl != float('inf') else 'inf',
                    size=len(self.cache))

    def _evict_oldest(self) -> None:
        """Evict oldest (LRU) entry"""
        if self.cache:
            key, entry = self.cache.popitem(last=False)
            self.evictions += 1
            logger.debug("cache_eviction", evictions=self.evictions)

    def clear(self) -> None:
        """Clear all cache"""
        self.cache.clear()
        logger.info("cache_cleared")

    def get_stats(self) -> Dict:
        """Get cache statistics"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0

        return {
            'enabled': self.enabled,
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': round(hit_rate, 1),
            'evictions': self.evictions
        }
