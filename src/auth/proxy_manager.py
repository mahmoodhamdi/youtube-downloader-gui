"""Proxy management for YouTube downloads.

This module provides proxy/VPN support for bypassing geo-restrictions
and protecting privacy.
"""

import os
import re
import socket
from typing import Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse


class ProxyType(Enum):
    """Supported proxy types."""
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"
    SOCKS5H = "socks5h"  # SOCKS5 with remote DNS


@dataclass
class ProxyConfig:
    """Proxy configuration.

    Attributes:
        proxy_type: Type of proxy (http, socks5, etc.)
        host: Proxy server hostname or IP
        port: Proxy server port
        username: Authentication username (optional)
        password: Authentication password (optional)
    """
    proxy_type: ProxyType
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None

    def to_url(self) -> str:
        """Convert to proxy URL format.

        Returns:
            Proxy URL string
        """
        if self.username and self.password:
            return f"{self.proxy_type.value}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.proxy_type.value}://{self.host}:{self.port}"

    @classmethod
    def from_url(cls, url: str) -> Optional['ProxyConfig']:
        """Create ProxyConfig from URL string.

        Args:
            url: Proxy URL (e.g., socks5://user:pass@host:port)

        Returns:
            ProxyConfig or None if invalid
        """
        try:
            parsed = urlparse(url)

            # Determine proxy type
            scheme = parsed.scheme.lower()
            try:
                proxy_type = ProxyType(scheme)
            except ValueError:
                return None

            host = parsed.hostname
            port = parsed.port

            if not host or not port:
                return None

            return cls(
                proxy_type=proxy_type,
                host=host,
                port=port,
                username=parsed.username,
                password=parsed.password
            )
        except Exception:
            return None


@dataclass
class ProxyTestResult:
    """Result of proxy test.

    Attributes:
        success: Whether test was successful
        latency_ms: Response time in milliseconds
        ip_address: Detected IP address through proxy
        country: Detected country (if available)
        error: Error message if test failed
    """
    success: bool
    latency_ms: Optional[float] = None
    ip_address: Optional[str] = None
    country: Optional[str] = None
    error: Optional[str] = None


class ProxyManager:
    """Manage proxy connections for downloads.

    Features:
    - Support HTTP, HTTPS, SOCKS4, SOCKS5 proxies
    - Proxy authentication
    - Connection testing
    - Proxy rotation from list
    - yt-dlp integration

    Usage:
        proxy = ProxyManager()

        # Set single proxy
        proxy.set_proxy("socks5", "127.0.0.1", 1080)

        # Or with authentication
        proxy.set_proxy("http", "proxy.example.com", 8080,
                       username="user", password="pass")

        # Test connection
        result = proxy.test_connection()
        if result.success:
            print(f"Proxy working, IP: {result.ip_address}")

        # Get yt-dlp options
        ydl_opts = proxy.get_ydl_opts()
    """

    PROXY_TYPES = [p.value for p in ProxyType]

    def __init__(self):
        """Initialize proxy manager."""
        self._current_proxy: Optional[ProxyConfig] = None
        self._proxy_list: List[ProxyConfig] = []
        self._proxy_index: int = 0
        self._enabled: bool = False

    def set_proxy(self, proxy_type: str, host: str, port: int,
                  username: Optional[str] = None,
                  password: Optional[str] = None) -> Tuple[bool, str]:
        """Set proxy configuration.

        Args:
            proxy_type: Type of proxy (http, https, socks4, socks5, socks5h)
            host: Proxy server hostname or IP
            port: Proxy server port
            username: Authentication username (optional)
            password: Authentication password (optional)

        Returns:
            Tuple of (success, message)
        """
        proxy_type_lower = proxy_type.lower()

        if proxy_type_lower not in self.PROXY_TYPES:
            return False, f"Invalid proxy type. Use one of: {', '.join(self.PROXY_TYPES)}"

        # Validate host
        if not host or not host.strip():
            return False, "Proxy host cannot be empty"

        # Validate port
        if not isinstance(port, int) or port < 1 or port > 65535:
            return False, "Invalid port number (must be 1-65535)"

        try:
            proxy_type_enum = ProxyType(proxy_type_lower)
            self._current_proxy = ProxyConfig(
                proxy_type=proxy_type_enum,
                host=host.strip(),
                port=port,
                username=username,
                password=password
            )
            self._enabled = True
            return True, f"Proxy set: {self._current_proxy.to_url()}"
        except Exception as e:
            return False, f"Failed to set proxy: {e}"

    def set_proxy_url(self, url: str) -> Tuple[bool, str]:
        """Set proxy from URL string.

        Args:
            url: Proxy URL (e.g., socks5://user:pass@host:port)

        Returns:
            Tuple of (success, message)
        """
        config = ProxyConfig.from_url(url)
        if config:
            self._current_proxy = config
            self._enabled = True
            return True, f"Proxy set: {config.host}:{config.port}"
        return False, "Invalid proxy URL format"

    def clear_proxy(self):
        """Clear proxy configuration."""
        self._current_proxy = None
        self._enabled = False

    def enable(self):
        """Enable proxy."""
        self._enabled = True

    def disable(self):
        """Disable proxy (keeps configuration)."""
        self._enabled = False

    def is_enabled(self) -> bool:
        """Check if proxy is enabled and configured."""
        return self._enabled and self._current_proxy is not None

    def get_proxy_url(self) -> Optional[str]:
        """Get current proxy URL.

        Returns:
            Proxy URL or None if not configured
        """
        if self._current_proxy and self._enabled:
            return self._current_proxy.to_url()
        return None

    def test_connection(self, timeout: int = 10) -> ProxyTestResult:
        """Test if proxy is working.

        Args:
            timeout: Connection timeout in seconds

        Returns:
            ProxyTestResult with test results
        """
        if not self._current_proxy:
            return ProxyTestResult(
                success=False,
                error="No proxy configured"
            )

        import time

        try:
            import requests

            proxy_url = self._current_proxy.to_url()
            proxies = {
                'http': proxy_url,
                'https': proxy_url
            }

            start_time = time.time()

            # Test with httpbin to get IP info
            response = requests.get(
                'https://httpbin.org/ip',
                proxies=proxies,
                timeout=timeout
            )

            latency = (time.time() - start_time) * 1000  # Convert to ms

            if response.status_code == 200:
                data = response.json()
                ip_address = data.get('origin', '').split(',')[0].strip()

                return ProxyTestResult(
                    success=True,
                    latency_ms=latency,
                    ip_address=ip_address
                )
            else:
                return ProxyTestResult(
                    success=False,
                    error=f"HTTP {response.status_code}"
                )

        except requests.exceptions.ProxyError as e:
            return ProxyTestResult(
                success=False,
                error=f"Proxy error: {e}"
            )
        except requests.exceptions.Timeout:
            return ProxyTestResult(
                success=False,
                error="Connection timeout"
            )
        except requests.exceptions.RequestException as e:
            return ProxyTestResult(
                success=False,
                error=str(e)
            )
        except ImportError:
            # Fallback: just test socket connection
            return self._test_socket_connection(timeout)

    def _test_socket_connection(self, timeout: int) -> ProxyTestResult:
        """Test proxy using socket connection.

        Args:
            timeout: Connection timeout

        Returns:
            ProxyTestResult
        """
        if not self._current_proxy:
            return ProxyTestResult(success=False, error="No proxy configured")

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((self._current_proxy.host, self._current_proxy.port))
            sock.close()
            return ProxyTestResult(
                success=True,
                error=None
            )
        except socket.error as e:
            return ProxyTestResult(
                success=False,
                error=f"Connection failed: {e}"
            )

    def get_ydl_opts(self) -> dict:
        """Get yt-dlp options for proxy.

        Returns:
            Dictionary of yt-dlp options
        """
        if self._enabled and self._current_proxy:
            return {'proxy': self._current_proxy.to_url()}
        return {}

    def add_to_proxy_list(self, config: ProxyConfig):
        """Add proxy to rotation list.

        Args:
            config: Proxy configuration
        """
        self._proxy_list.append(config)

    def add_proxy_url_to_list(self, url: str) -> bool:
        """Add proxy URL to rotation list.

        Args:
            url: Proxy URL

        Returns:
            True if added successfully
        """
        config = ProxyConfig.from_url(url)
        if config:
            self._proxy_list.append(config)
            return True
        return False

    def rotate_proxy(self) -> bool:
        """Rotate to next proxy in list.

        Returns:
            True if rotated successfully
        """
        if not self._proxy_list:
            return False

        self._proxy_index = (self._proxy_index + 1) % len(self._proxy_list)
        self._current_proxy = self._proxy_list[self._proxy_index]
        return True

    def clear_proxy_list(self):
        """Clear proxy rotation list."""
        self._proxy_list.clear()
        self._proxy_index = 0

    def get_config(self) -> Optional[ProxyConfig]:
        """Get current proxy configuration.

        Returns:
            ProxyConfig or None
        """
        return self._current_proxy if self._enabled else None

    @staticmethod
    def validate_proxy_url(url: str) -> Tuple[bool, str]:
        """Validate a proxy URL format.

        Args:
            url: Proxy URL to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        config = ProxyConfig.from_url(url)
        if config:
            return True, ""
        return False, "Invalid proxy URL format. Expected: protocol://[user:pass@]host:port"
