"""Authentication module for YouTube Downloader.

This module provides authentication and proxy support:
- Cookie-based authentication (browser import or file)
- Proxy/VPN support (HTTP, SOCKS4, SOCKS5)
"""

from .auth_manager import AuthManager, AuthStatus, BrowserType
from .proxy_manager import ProxyManager, ProxyConfig, ProxyType, ProxyTestResult

__all__ = [
    # Auth Manager
    'AuthManager',
    'AuthStatus',
    'BrowserType',
    # Proxy Manager
    'ProxyManager',
    'ProxyConfig',
    'ProxyType',
    'ProxyTestResult',
]
