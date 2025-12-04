"""Caching utilities for YouTube Downloader.

This module provides thread-safe caching with:
- LRU (Least Recently Used) eviction
- TTL (Time To Live) expiration
- Size-based eviction
- Memory usage tracking
"""

import threading
import time
import sys
import hashlib
from collections import OrderedDict
from typing import Any, Optional, Dict, Callable, TypeVar, Generic
from dataclasses import dataclass
from datetime import datetime, timedelta


T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    """Represents a cached item with metadata.

    Attributes:
        value: The cached value
        created_at: When the entry was created
        accessed_at: When the entry was last accessed
        access_count: Number of times accessed
        size_bytes: Estimated size in bytes
        ttl: Time to live in seconds (None = no expiration)
    """
    value: T
    created_at: float
    accessed_at: float
    access_count: int = 0
    size_bytes: int = 0
    ttl: Optional[float] = None

    def is_expired(self) -> bool:
        """Check if this entry has expired."""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl

    def touch(self):
        """Update access time and count."""
        self.accessed_at = time.time()
        self.access_count += 1


class CacheManager(Generic[T]):
    """Thread-safe LRU cache with TTL support.

    Features:
    - Thread-safe operations
    - LRU eviction when max size reached
    - TTL-based expiration
    - Memory usage tracking
    - Statistics and monitoring

    Usage:
        cache = CacheManager[VideoInfo](max_size=100, default_ttl=3600)
        cache.set("video_id", video_info)
        info = cache.get("video_id")
    """

    def __init__(
        self,
        max_size: int = 1000,
        max_memory_mb: Optional[float] = None,
        default_ttl: Optional[float] = None,
        on_evict: Optional[Callable[[str, T], None]] = None
    ):
        """Initialize the cache.

        Args:
            max_size: Maximum number of items
            max_memory_mb: Maximum memory usage in MB (None = unlimited)
            default_ttl: Default TTL in seconds (None = no expiration)
            on_evict: Callback when items are evicted
        """
        self._cache: OrderedDict[str, CacheEntry[T]] = OrderedDict()
        self._lock = threading.RLock()
        self.max_size = max_size
        self.max_memory_bytes = int(max_memory_mb * 1024 * 1024) if max_memory_mb else None
        self.default_ttl = default_ttl
        self.on_evict = on_evict

        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def get(self, key: str, default: T = None) -> Optional[T]:
        """Get a value from the cache.

        Args:
            key: Cache key
            default: Default value if not found

        Returns:
            Cached value or default
        """
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return default

            entry = self._cache[key]

            # Check expiration
            if entry.is_expired():
                self._remove(key)
                self._misses += 1
                return default

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.touch()
            self._hits += 1

            return entry.value

    def set(
        self,
        key: str,
        value: T,
        ttl: Optional[float] = None
    ) -> bool:
        """Set a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: TTL in seconds (None = use default)

        Returns:
            True if set successfully
        """
        with self._lock:
            # Calculate size
            size_bytes = self._estimate_size(value)

            # Create entry
            entry = CacheEntry(
                value=value,
                created_at=time.time(),
                accessed_at=time.time(),
                size_bytes=size_bytes,
                ttl=ttl if ttl is not None else self.default_ttl
            )

            # Remove existing entry if present
            if key in self._cache:
                self._remove(key)

            # Evict if necessary
            self._evict_if_needed(size_bytes)

            # Add new entry
            self._cache[key] = entry
            return True

    def delete(self, key: str) -> bool:
        """Delete a key from the cache.

        Args:
            key: Key to delete

        Returns:
            True if key was deleted
        """
        with self._lock:
            if key in self._cache:
                self._remove(key)
                return True
            return False

    def clear(self):
        """Clear all entries from the cache."""
        with self._lock:
            # Call eviction callback for all entries
            if self.on_evict:
                for key, entry in self._cache.items():
                    try:
                        self.on_evict(key, entry.value)
                    except Exception:
                        pass

            self._cache.clear()

    def contains(self, key: str) -> bool:
        """Check if key exists and is not expired.

        Args:
            key: Key to check

        Returns:
            True if key exists and is valid
        """
        with self._lock:
            if key not in self._cache:
                return False

            entry = self._cache[key]
            if entry.is_expired():
                self._remove(key)
                return False

            return True

    def _remove(self, key: str):
        """Remove an entry and call eviction callback."""
        if key in self._cache:
            entry = self._cache.pop(key)
            if self.on_evict:
                try:
                    self.on_evict(key, entry.value)
                except Exception:
                    pass

    def _evict_if_needed(self, new_size: int = 0):
        """Evict entries if cache is over limits."""
        # Evict expired entries first
        expired = [k for k, v in self._cache.items() if v.is_expired()]
        for key in expired:
            self._remove(key)
            self._evictions += 1

        # Check size limit
        while len(self._cache) >= self.max_size:
            # Remove oldest entry (LRU)
            key = next(iter(self._cache))
            self._remove(key)
            self._evictions += 1

        # Check memory limit
        if self.max_memory_bytes:
            current_memory = self.get_memory_usage()
            while current_memory + new_size > self.max_memory_bytes and self._cache:
                key = next(iter(self._cache))
                self._remove(key)
                self._evictions += 1
                current_memory = self.get_memory_usage()

    def _estimate_size(self, value: Any) -> int:
        """Estimate the size of a value in bytes."""
        try:
            return sys.getsizeof(value)
        except Exception:
            return 0

    def get_memory_usage(self) -> int:
        """Get estimated memory usage in bytes."""
        with self._lock:
            return sum(entry.size_bytes for entry in self._cache.values())

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'memory_bytes': self.get_memory_usage(),
                'hits': self._hits,
                'misses': self._misses,
                'evictions': self._evictions,
                'hit_rate': f"{hit_rate:.1f}%",
            }

    def cleanup_expired(self) -> int:
        """Remove all expired entries.

        Returns:
            Number of entries removed
        """
        with self._lock:
            expired = [k for k, v in self._cache.items() if v.is_expired()]
            for key in expired:
                self._remove(key)
            return len(expired)

    def keys(self) -> list:
        """Get all valid keys."""
        with self._lock:
            return [k for k, v in self._cache.items() if not v.is_expired()]

    def values(self) -> list:
        """Get all valid values."""
        with self._lock:
            return [v.value for v in self._cache.values() if not v.is_expired()]

    def items(self) -> list:
        """Get all valid key-value pairs."""
        with self._lock:
            return [
                (k, v.value)
                for k, v in self._cache.items()
                if not v.is_expired()
            ]

    def __len__(self) -> int:
        return len(self._cache)

    def __contains__(self, key: str) -> bool:
        return self.contains(key)


class ThumbnailCache(CacheManager):
    """Specialized cache for thumbnail images.

    Optimized for storing PIL Image or PhotoImage objects
    with automatic memory management.
    """

    def __init__(
        self,
        max_size: int = 100,
        max_memory_mb: float = 50.0
    ):
        super().__init__(
            max_size=max_size,
            max_memory_mb=max_memory_mb,
            default_ttl=3600  # 1 hour TTL
        )

    def get_by_url(self, url: str):
        """Get thumbnail by URL (hashed as key)."""
        key = self._hash_url(url)
        return self.get(key)

    def set_by_url(self, url: str, image):
        """Set thumbnail by URL."""
        key = self._hash_url(url)
        return self.set(key, image)

    @staticmethod
    def _hash_url(url: str) -> str:
        """Create a hash key from URL."""
        return hashlib.md5(url.encode()).hexdigest()


class VideoInfoCache(CacheManager):
    """Specialized cache for video metadata.

    Stores video information with longer TTL since
    video metadata rarely changes.
    """

    def __init__(
        self,
        max_size: int = 500,
        default_ttl: float = 7200  # 2 hours
    ):
        super().__init__(
            max_size=max_size,
            default_ttl=default_ttl
        )

    def get_by_url(self, url: str):
        """Get video info by URL."""
        key = self._normalize_url(url)
        return self.get(key)

    def set_by_url(self, url: str, info: dict):
        """Set video info by URL."""
        key = self._normalize_url(url)
        return self.set(key, info)

    @staticmethod
    def _normalize_url(url: str) -> str:
        """Normalize URL for consistent cache keys."""
        # Extract video ID if possible
        import re
        patterns = [
            r'(?:v=|/)([a-zA-Z0-9_-]{11})(?:\?|&|$)',
            r'youtu\.be/([a-zA-Z0-9_-]{11})',
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return f"video:{match.group(1)}"

        # Fallback to hash
        return hashlib.md5(url.encode()).hexdigest()
