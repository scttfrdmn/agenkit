"""Caching middleware with LRU eviction and TTL expiration."""

import asyncio
import hashlib
import json
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field

from agenkit.interfaces import Agent, Message


class AsyncRWLock:
    """Async read-write lock allowing multiple concurrent readers or single writer.

    This implementation is GIL-free safe and works correctly with Python 3.13+
    free-threaded mode. It uses asyncio primitives for proper async coordination.
    Handles task cancellation gracefully.
    """

    def __init__(self):
        """Initialize the read-write lock."""
        self._readers = 0
        self._writer = False
        self._lock = asyncio.Lock()  # Protects _readers and _writer
        self._read_ok = asyncio.Condition(self._lock)
        self._write_ok = asyncio.Condition(self._lock)

    async def acquire_read(self):
        """Acquire read lock (multiple readers allowed concurrently)."""
        try:
            async with self._lock:
                # Wait until no writer
                while self._writer:
                    await self._read_ok.wait()
                self._readers += 1
        except asyncio.CancelledError:
            # If cancelled while waiting, ensure we don't hold any locks
            raise

    async def release_read(self):
        """Release read lock."""
        try:
            async with self._lock:
                self._readers -= 1
                # If last reader, notify waiting writer
                if self._readers == 0:
                    self._write_ok.notify()
        except asyncio.CancelledError:
            # If cancelled during release, try to complete the release
            try:
                async with self._lock:
                    if self._readers > 0:
                        self._readers -= 1
                    if self._readers == 0:
                        self._write_ok.notify()
            except Exception:
                pass
            raise

    async def acquire_write(self):
        """Acquire write lock (exclusive access)."""
        try:
            async with self._lock:
                # Wait until no readers and no writer
                while self._readers > 0 or self._writer:
                    await self._write_ok.wait()
                self._writer = True
        except asyncio.CancelledError:
            # If cancelled while waiting, ensure we don't hold any locks
            raise

    async def release_write(self):
        """Release write lock."""
        try:
            async with self._lock:
                self._writer = False
                # Notify all waiting readers and one waiting writer
                self._read_ok.notify_all()
                self._write_ok.notify()
        except asyncio.CancelledError:
            # If cancelled during release, try to complete the release
            try:
                async with self._lock:
                    self._writer = False
                    self._read_ok.notify_all()
                    self._write_ok.notify()
            except Exception:
                pass
            raise


@dataclass
class CachingConfig:
    """Configuration for caching behavior."""

    max_cache_size: int = 1000
    default_ttl: float = 300.0  # 5 minutes in seconds
    key_generator: Callable[[Message], str] | None = None

    def __post_init__(self):
        """Validate configuration."""
        if self.max_cache_size < 1:
            raise ValueError("max_cache_size must be at least 1")
        if self.default_ttl <= 0:
            raise ValueError("default_ttl must be positive")


@dataclass
class CachingMetrics:
    """Metrics for cache operations."""

    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    evictions: int = 0
    invalidations: int = 0
    current_size: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        if self.total_requests == 0:
            return 0.0
        return self.cache_hits / self.total_requests

    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate."""
        if self.total_requests == 0:
            return 0.0
        return self.cache_misses / self.total_requests


@dataclass
class CacheEntry:
    """Entry in the cache with expiration."""

    response: Message
    expires_at: float
    created_at: float = field(default_factory=time.time)

    def is_expired(self) -> bool:
        """Check if entry is expired."""
        return time.time() >= self.expires_at


class CachingDecorator(Agent):
    """Agent decorator that caches responses with LRU eviction and TTL expiration."""

    def __init__(self, agent: Agent, config: CachingConfig | None = None):
        """Initialize caching decorator.

        Args:
            agent: The agent to wrap
            config: Caching configuration (uses defaults if not provided)
        """
        self._agent = agent
        self._config = config or CachingConfig()
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._rwlock = AsyncRWLock()
        self._metrics = CachingMetrics()

    @property
    def name(self) -> str:
        """Return the name of the underlying agent."""
        return self._agent.name

    @property
    def capabilities(self) -> list[str]:
        """Return capabilities of the underlying agent."""
        return self._agent.capabilities

    @property
    def metrics(self) -> CachingMetrics:
        """Return caching metrics."""
        return self._metrics

    def _generate_cache_key(self, message: Message) -> str:
        """Generate cache key from message.

        Args:
            message: Input message

        Returns:
            Cache key string
        """
        if self._config.key_generator:
            return self._config.key_generator(message)

        # Default key generation: hash of role + content + metadata
        key_data = {
            "role": message.role,
            "content": str(message.content),
            "metadata": message.metadata or {},
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()

    async def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if len(self._cache) >= self._config.max_cache_size:
            # Remove oldest (LRU) entry
            self._cache.popitem(last=False)
            self._metrics.evictions += 1
            self._metrics.current_size = len(self._cache)

    async def _cleanup_expired(self) -> None:
        """Remove expired entries from cache."""
        expired_keys = [key for key, entry in self._cache.items() if entry.is_expired()]
        for key in expired_keys:
            del self._cache[key]
            self._metrics.evictions += 1
        if expired_keys:
            self._metrics.current_size = len(self._cache)

    async def process(self, message: Message) -> Message:
        """Process message with caching.

        Args:
            message: Input message

        Returns:
            Response message from cache or agent

        Raises:
            Exception: If agent processing fails
        """
        # Increment metrics (atomic operation for approximate metrics)
        self._metrics.total_requests += 1

        # Generate cache key (no lock needed)
        cache_key = self._generate_cache_key(message)

        # Check cache with read lock (allows concurrent reads)
        await self._rwlock.acquire_read()
        try:
            if cache_key in self._cache:
                entry = self._cache[cache_key]

                # Check if expired
                if not entry.is_expired():
                    # Cache hit - return cached response
                    # Note: We don't move_to_end to avoid upgrading to write lock
                    response = entry.response
                    await self._rwlock.release_read()
                    self._metrics.cache_hits += 1
                    return response

            # Not in cache or expired
            await self._rwlock.release_read()
        except Exception:
            await self._rwlock.release_read()
            raise

        # Cache miss
        self._metrics.cache_misses += 1

        # Process message (outside lock to avoid blocking cache operations)
        response = await self._agent.process(message)

        # Cache response with write lock
        await self._rwlock.acquire_write()
        try:
            # Cleanup expired entries periodically
            if self._metrics.total_requests % 100 == 0:
                await self._cleanup_expired()

            # Evict LRU if needed
            await self._evict_lru()

            # Add to cache
            entry = CacheEntry(
                response=response,
                expires_at=time.time() + self._config.default_ttl,
            )
            self._cache[cache_key] = entry
            self._metrics.current_size = len(self._cache)
        finally:
            await self._rwlock.release_write()

        return response

    async def stream(self, message: Message):
        """Stream responses (caching not supported for streaming).

        For streaming, we bypass the cache since partial responses
        can't be effectively cached.

        Args:
            message: Input message

        Yields:
            Response messages from agent
        """
        # Streaming bypasses cache
        async for chunk in self._agent.stream(message):
            yield chunk

    async def invalidate(self, message: Message | None = None) -> None:
        """Invalidate cache entries.

        Args:
            message: If provided, invalidate only this message's cache entry.
                    If None, invalidate entire cache.
        """
        await self._rwlock.acquire_write()
        try:
            if message is not None:
                # Invalidate specific entry
                cache_key = self._generate_cache_key(message)
                if cache_key in self._cache:
                    del self._cache[cache_key]
                    self._metrics.invalidations += 1
                    self._metrics.current_size = len(self._cache)
            else:
                # Invalidate entire cache
                count = len(self._cache)
                self._cache.clear()
                self._metrics.invalidations += count
                self._metrics.current_size = 0
        finally:
            await self._rwlock.release_write()

    async def get_cache_size(self) -> int:
        """Get current cache size.

        Returns:
            Number of entries in cache
        """
        await self._rwlock.acquire_read()
        try:
            return len(self._cache)
        finally:
            await self._rwlock.release_read()

    async def get_cache_info(self) -> dict:
        """Get detailed cache information.

        Returns:
            Dictionary with cache statistics
        """
        await self._rwlock.acquire_read()
        try:
            return {
                "size": len(self._cache),
                "max_size": self._config.max_cache_size,
                "default_ttl": self._config.default_ttl,
                "metrics": {
                    "total_requests": self._metrics.total_requests,
                    "cache_hits": self._metrics.cache_hits,
                    "cache_misses": self._metrics.cache_misses,
                    "hit_rate": self._metrics.hit_rate,
                    "miss_rate": self._metrics.miss_rate,
                    "evictions": self._metrics.evictions,
                    "invalidations": self._metrics.invalidations,
                },
            }
        finally:
            await self._rwlock.release_read()
