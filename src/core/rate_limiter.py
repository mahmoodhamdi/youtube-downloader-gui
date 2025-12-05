"""Rate limiting for YouTube downloads.

This module provides rate limiting to avoid IP bans and throttling.
"""

import time
import random
import threading
from typing import Optional
from collections import deque
from dataclasses import dataclass


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting.

    Attributes:
        requests_per_minute: Maximum requests per minute
        min_delay: Minimum delay between requests (seconds)
        max_delay: Maximum delay between requests (seconds)
        burst_limit: Maximum burst requests allowed
        cooldown_seconds: Cooldown period after hitting limit
    """
    requests_per_minute: int = 30
    min_delay: float = 1.0
    max_delay: float = 3.0
    burst_limit: int = 5
    cooldown_seconds: int = 60


class RateLimiter:
    """Rate limiter to prevent IP bans from YouTube.

    Features:
    - Track request frequency
    - Enforce rate limits
    - Add random delays to avoid detection
    - Support burst requests with cooldown
    - Thread-safe operations

    Usage:
        limiter = RateLimiter(requests_per_minute=30)

        # Before each request
        limiter.wait_if_needed()

        # Add delay between downloads
        limiter.add_delay_between_downloads()

        # Check if we should slow down
        if limiter.is_rate_limited():
            # Wait or queue request
            pass
    """

    def __init__(self, config: Optional[RateLimitConfig] = None):
        """Initialize rate limiter.

        Args:
            config: Rate limit configuration
        """
        self.config = config or RateLimitConfig()
        self._lock = threading.RLock()
        self._request_times: deque = deque()
        self._last_request_time: float = 0
        self._burst_count: int = 0
        self._cooldown_until: float = 0

    def wait_if_needed(self) -> float:
        """Wait if we're exceeding rate limit.

        Returns:
            Actual wait time in seconds
        """
        with self._lock:
            now = time.time()
            waited = 0.0

            # Check if in cooldown period
            if now < self._cooldown_until:
                wait_time = self._cooldown_until - now
                time.sleep(wait_time)
                waited = wait_time
                now = time.time()

            # Clean old request times (older than 1 minute)
            while self._request_times and now - self._request_times[0] > 60:
                self._request_times.popleft()

            # Check if we've exceeded rate limit
            if len(self._request_times) >= self.config.requests_per_minute:
                # Calculate wait time
                oldest_request = self._request_times[0]
                wait_time = 60 - (now - oldest_request) + 0.1  # Small buffer
                if wait_time > 0:
                    time.sleep(wait_time)
                    waited += wait_time
                    now = time.time()

            # Record this request
            self._request_times.append(now)
            self._last_request_time = now

            return waited

    def add_delay_between_downloads(self, min_delay: Optional[float] = None,
                                    max_delay: Optional[float] = None) -> float:
        """Add random delay between downloads to avoid detection.

        Args:
            min_delay: Minimum delay (uses config default if None)
            max_delay: Maximum delay (uses config default if None)

        Returns:
            Actual delay applied
        """
        min_d = min_delay if min_delay is not None else self.config.min_delay
        max_d = max_delay if max_delay is not None else self.config.max_delay

        delay = random.uniform(min_d, max_d)
        time.sleep(delay)
        return delay

    def is_rate_limited(self) -> bool:
        """Check if currently rate limited.

        Returns:
            True if rate limited
        """
        with self._lock:
            now = time.time()

            # Check cooldown
            if now < self._cooldown_until:
                return True

            # Clean old requests
            while self._request_times and now - self._request_times[0] > 60:
                self._request_times.popleft()

            return len(self._request_times) >= self.config.requests_per_minute

    def record_request(self):
        """Record a request without waiting."""
        with self._lock:
            self._request_times.append(time.time())
            self._last_request_time = time.time()

    def trigger_cooldown(self, duration: Optional[int] = None):
        """Trigger a cooldown period.

        Args:
            duration: Cooldown duration in seconds (uses config default if None)
        """
        with self._lock:
            duration = duration or self.config.cooldown_seconds
            self._cooldown_until = time.time() + duration

    def get_wait_time(self) -> float:
        """Get estimated wait time before next request allowed.

        Returns:
            Wait time in seconds (0 if no wait needed)
        """
        with self._lock:
            now = time.time()

            # Check cooldown
            if now < self._cooldown_until:
                return self._cooldown_until - now

            # Clean old requests
            while self._request_times and now - self._request_times[0] > 60:
                self._request_times.popleft()

            if len(self._request_times) >= self.config.requests_per_minute:
                oldest_request = self._request_times[0]
                return max(0, 60 - (now - oldest_request))

            return 0

    def get_requests_remaining(self) -> int:
        """Get number of requests remaining in current window.

        Returns:
            Number of requests allowed
        """
        with self._lock:
            now = time.time()

            # Clean old requests
            while self._request_times and now - self._request_times[0] > 60:
                self._request_times.popleft()

            return max(0, self.config.requests_per_minute - len(self._request_times))

    def reset(self):
        """Reset rate limiter state."""
        with self._lock:
            self._request_times.clear()
            self._last_request_time = 0
            self._burst_count = 0
            self._cooldown_until = 0

    def handle_rate_limit_error(self):
        """Handle a rate limit error from YouTube.

        This triggers an extended cooldown.
        """
        with self._lock:
            # Double the cooldown on rate limit errors
            extended_cooldown = self.config.cooldown_seconds * 2
            self._cooldown_until = time.time() + extended_cooldown
            self._burst_count = 0

    def can_burst(self) -> bool:
        """Check if burst request is allowed.

        Returns:
            True if burst is allowed
        """
        with self._lock:
            return self._burst_count < self.config.burst_limit

    def record_burst(self):
        """Record a burst request."""
        with self._lock:
            self._burst_count += 1

    def reset_burst(self):
        """Reset burst counter."""
        with self._lock:
            self._burst_count = 0


class AdaptiveRateLimiter(RateLimiter):
    """Adaptive rate limiter that adjusts based on server responses.

    This extends RateLimiter to automatically adjust rate limits
    based on success/failure patterns.
    """

    def __init__(self, config: Optional[RateLimitConfig] = None):
        """Initialize adaptive rate limiter."""
        super().__init__(config)
        self._success_count = 0
        self._failure_count = 0
        self._original_rpm = self.config.requests_per_minute

    def record_success(self):
        """Record a successful request."""
        with self._lock:
            self._success_count += 1
            self._failure_count = 0  # Reset failure streak

            # Gradually increase rate limit after consistent success
            if self._success_count >= 10:
                self.config.requests_per_minute = min(
                    self._original_rpm,
                    self.config.requests_per_minute + 1
                )
                self._success_count = 0

    def record_failure(self):
        """Record a failed request (e.g., rate limit error)."""
        with self._lock:
            self._failure_count += 1
            self._success_count = 0  # Reset success streak

            # Reduce rate limit on failures
            if self._failure_count >= 2:
                self.config.requests_per_minute = max(
                    5,  # Minimum RPM
                    self.config.requests_per_minute // 2
                )
                self._failure_count = 0
                self.trigger_cooldown()

    def get_stats(self) -> dict:
        """Get rate limiter statistics.

        Returns:
            Dictionary with stats
        """
        with self._lock:
            return {
                'current_rpm': self.config.requests_per_minute,
                'original_rpm': self._original_rpm,
                'success_streak': self._success_count,
                'failure_streak': self._failure_count,
                'requests_in_window': len(self._request_times),
                'wait_time': self.get_wait_time(),
            }
