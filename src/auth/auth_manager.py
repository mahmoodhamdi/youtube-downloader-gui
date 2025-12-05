"""Authentication management for YouTube downloads.

This module provides cookie-based authentication for accessing
age-restricted or members-only content.
"""

import os
import shutil
from typing import Optional, List, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum


class BrowserType(Enum):
    """Supported browsers for cookie extraction."""
    CHROME = "chrome"
    FIREFOX = "firefox"
    EDGE = "edge"
    OPERA = "opera"
    BRAVE = "brave"
    CHROMIUM = "chromium"
    SAFARI = "safari"
    VIVALDI = "vivaldi"


@dataclass
class AuthStatus:
    """Authentication status.

    Attributes:
        is_authenticated: Whether authentication is configured
        method: Authentication method (cookies_file, browser, none)
        browser: Browser used for extraction (if applicable)
        cookies_file: Path to cookies file (if applicable)
        error: Error message if authentication failed
    """
    is_authenticated: bool = False
    method: str = "none"
    browser: Optional[str] = None
    cookies_file: Optional[str] = None
    error: Optional[str] = None


class AuthManager:
    """Manage authentication for YouTube.

    Features:
    - Import cookies from browsers (Chrome, Firefox, Edge, etc.)
    - Import cookies from Netscape format file
    - Validate cookie files
    - Provide yt-dlp options for authentication

    Usage:
        auth = AuthManager()

        # Import from browser
        if auth.import_cookies_from_browser("chrome"):
            print("Cookies imported successfully")

        # Or import from file
        auth.import_cookies_file("/path/to/cookies.txt")

        # Get yt-dlp options
        ydl_opts = auth.get_ydl_opts()
    """

    SUPPORTED_BROWSERS = [b.value for b in BrowserType]

    def __init__(self, cookies_dir: str = "cookies"):
        """Initialize authentication manager.

        Args:
            cookies_dir: Directory to store cookie files
        """
        self.cookies_dir = cookies_dir
        self._cookies_file: Optional[str] = None
        self._browser: Optional[str] = None
        self._use_browser_cookies: bool = False

        # Create cookies directory
        os.makedirs(cookies_dir, exist_ok=True)

        # Check for existing cookies
        self._detect_existing_cookies()

    def _detect_existing_cookies(self):
        """Detect existing cookie configuration."""
        cookies_path = os.path.join(self.cookies_dir, "cookies.txt")
        if os.path.exists(cookies_path):
            self._cookies_file = cookies_path

    def import_cookies_from_browser(self, browser: str = "chrome") -> Tuple[bool, str]:
        """Import cookies from browser.

        Note: This sets up yt-dlp to extract cookies directly from the browser
        at download time. It doesn't copy the cookies to a file.

        Args:
            browser: Browser name (chrome, firefox, edge, etc.)

        Returns:
            Tuple of (success, message)
        """
        browser_lower = browser.lower()

        if browser_lower not in self.SUPPORTED_BROWSERS:
            return False, f"Unsupported browser. Use one of: {', '.join(self.SUPPORTED_BROWSERS)}"

        # Verify browser is installed (basic check)
        if not self._is_browser_available(browser_lower):
            return False, f"Browser '{browser}' not found or not accessible"

        self._browser = browser_lower
        self._use_browser_cookies = True
        self._cookies_file = None

        return True, f"Will extract cookies from {browser} at download time"

    def _is_browser_available(self, browser: str) -> bool:
        """Check if browser is available for cookie extraction.

        Args:
            browser: Browser name

        Returns:
            True if browser appears to be available
        """
        # Basic checks for common browsers
        # yt-dlp will do more thorough checking
        import platform
        system = platform.system().lower()

        if system == "windows":
            browser_paths = {
                "chrome": [
                    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data"),
                ],
                "firefox": [
                    os.path.expandvars(r"%APPDATA%\Mozilla\Firefox\Profiles"),
                ],
                "edge": [
                    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data"),
                ],
                "brave": [
                    os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data"),
                ],
                "opera": [
                    os.path.expandvars(r"%APPDATA%\Opera Software\Opera Stable"),
                ],
            }
        elif system == "darwin":  # macOS
            browser_paths = {
                "chrome": [
                    os.path.expanduser("~/Library/Application Support/Google/Chrome"),
                ],
                "firefox": [
                    os.path.expanduser("~/Library/Application Support/Firefox/Profiles"),
                ],
                "safari": [
                    os.path.expanduser("~/Library/Cookies"),
                ],
                "edge": [
                    os.path.expanduser("~/Library/Application Support/Microsoft Edge"),
                ],
            }
        else:  # Linux
            browser_paths = {
                "chrome": [
                    os.path.expanduser("~/.config/google-chrome"),
                ],
                "firefox": [
                    os.path.expanduser("~/.mozilla/firefox"),
                ],
                "chromium": [
                    os.path.expanduser("~/.config/chromium"),
                ],
            }

        paths = browser_paths.get(browser, [])
        return any(os.path.exists(p) for p in paths)

    def import_cookies_file(self, file_path: str) -> Tuple[bool, str]:
        """Import cookies from Netscape format file.

        Args:
            file_path: Path to cookies.txt file

        Returns:
            Tuple of (success, message)
        """
        if not os.path.exists(file_path):
            return False, f"File not found: {file_path}"

        # Validate file format (basic check)
        if not self._validate_cookies_file(file_path):
            return False, "Invalid cookies file format. Expected Netscape format."

        # Copy to cookies directory
        dest_path = os.path.join(self.cookies_dir, "cookies.txt")
        try:
            shutil.copy(file_path, dest_path)
            self._cookies_file = dest_path
            self._use_browser_cookies = False
            self._browser = None
            return True, f"Cookies imported to {dest_path}"
        except IOError as e:
            return False, f"Failed to copy cookies file: {e}"

    def _validate_cookies_file(self, file_path: str) -> bool:
        """Validate Netscape cookies file format.

        Args:
            file_path: Path to cookies file

        Returns:
            True if file appears valid
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Check for Netscape format header or valid cookie lines
            for line in lines[:20]:  # Check first 20 lines
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                # Netscape format: domain, flag, path, secure, expiration, name, value
                parts = line.split('\t')
                if len(parts) >= 7:
                    return True

            return False
        except (IOError, UnicodeDecodeError):
            return False

    def clear_cookies(self) -> bool:
        """Clear stored cookies.

        Returns:
            True if cookies were cleared
        """
        self._cookies_file = None
        self._browser = None
        self._use_browser_cookies = False

        cookies_path = os.path.join(self.cookies_dir, "cookies.txt")
        if os.path.exists(cookies_path):
            try:
                os.remove(cookies_path)
                return True
            except IOError:
                return False
        return True

    def get_status(self) -> AuthStatus:
        """Get current authentication status.

        Returns:
            AuthStatus object
        """
        if self._use_browser_cookies and self._browser:
            return AuthStatus(
                is_authenticated=True,
                method="browser",
                browser=self._browser
            )
        elif self._cookies_file and os.path.exists(self._cookies_file):
            return AuthStatus(
                is_authenticated=True,
                method="cookies_file",
                cookies_file=self._cookies_file
            )
        else:
            return AuthStatus(
                is_authenticated=False,
                method="none"
            )

    def get_ydl_opts(self) -> dict:
        """Get yt-dlp options for authentication.

        Returns:
            Dictionary of yt-dlp options
        """
        opts = {}

        if self._use_browser_cookies and self._browser:
            # Extract cookies from browser at runtime
            opts['cookiesfrombrowser'] = (self._browser,)
        elif self._cookies_file and os.path.exists(self._cookies_file):
            # Use cookies file
            opts['cookiefile'] = self._cookies_file

        return opts

    def test_authentication(self, test_url: str = None) -> Tuple[bool, str]:
        """Test if authentication is working.

        Args:
            test_url: Optional URL to test with

        Returns:
            Tuple of (success, message)
        """
        try:
            import yt_dlp

            test_url = test_url or "https://www.youtube.com/feed/subscriptions"
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                **self.get_ydl_opts()
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Try to extract info - this will fail if not authenticated
                info = ydl.extract_info(test_url, download=False)
                if info:
                    return True, "Authentication successful"
                return False, "Authentication may not be working"

        except Exception as e:
            error_msg = str(e).lower()
            if "sign in" in error_msg or "login" in error_msg:
                return False, "Authentication required - cookies not valid"
            return False, f"Test failed: {e}"

    @property
    def is_authenticated(self) -> bool:
        """Check if authentication is configured."""
        return self.get_status().is_authenticated

    def get_available_browsers(self) -> List[str]:
        """Get list of available browsers for cookie extraction.

        Returns:
            List of browser names
        """
        available = []
        for browser in self.SUPPORTED_BROWSERS:
            if self._is_browser_available(browser):
                available.append(browser)
        return available
