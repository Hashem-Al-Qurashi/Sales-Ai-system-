"""
In-memory cache implementation.

Simple implementation for development and testing.
Can be replaced with Redis for production scaling.
"""

import time
from typing import Any, Optional, Dict
from threading import Lock
from dataclasses import dataclass

from ..core.logger import get_logger
from .interfaces import CacheInterface

logger = get_logger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with TTL support."""
    value: Any
    expires_at: Optional[float] = None


class MemoryCache(CacheInterface):
    """
    Thread-safe in-memory cache with TTL support.
    
    Follows ARCHITECTURE.md optimization points: "Chunk cache: 1000 most recent"
    """
    
    def __init__(self, max_size: int = 1000):
        """Initialize cache with size limit."""
        self.max_size = max_size
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = Lock()
        self._access_order = []  # For LRU eviction
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value with TTL check."""
        with self._lock:
            entry = self._cache.get(key)
            if not entry:
                return None
            
            # Check expiration
            if entry.expires_at and time.time() > entry.expires_at:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                return None
            
            # Update access order for LRU
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
            
            return entry.value
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Set cached value with optional TTL."""
        with self._lock:
            expires_at = None
            if ttl_seconds:
                expires_at = time.time() + ttl_seconds
            
            self._cache[key] = CacheEntry(value=value, expires_at=expires_at)
            
            # Update access order
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
            
            # Evict oldest if over limit
            while len(self._cache) > self.max_size:
                oldest_key = self._access_order.pop(0)
                if oldest_key in self._cache:
                    del self._cache[oldest_key]
    
    def delete(self, key: str) -> None:
        """Delete cached value."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
            if key in self._access_order:
                self._access_order.remove(key)
    
    def clear(self) -> None:
        """Clear all cached values."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
    
    def health_check(self) -> bool:
        """Check if cache is operational."""
        try:
            # Simple operation test
            test_key = "__health_check__"
            self.set(test_key, "ok")
            result = self.get(test_key)
            self.delete(test_key)
            return result == "ok"
        except Exception as e:
            logger.warning(f"Memory cache health check failed: {e}")
            return False