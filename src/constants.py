"""Application-wide constants for FitFetch.

Every magic number, URL, regex pattern, timeout, and string literal
lives here.  Other modules should import from this file rather than
hard-coding values.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------
VERSION = "1.4.2"
APP_NAME = "FitFetch"
OWNER = "BrainlessDip"

# ---------------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------------
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT = 10
CF_TIMEOUT = 30
MAX_CF_THREADS = 10
NETWORK_TIMEOUT = 8

# ---------------------------------------------------------------------------
# Timing
# ---------------------------------------------------------------------------
STARTUP_UPDATE_DELAY_MS = 1500
CLOSE_WAIT_MS = 3000

# ---------------------------------------------------------------------------
# Pre-compiled regexes
# ---------------------------------------------------------------------------
RE_PART_NUM = re.compile(r"part(\d+)", re.IGNORECASE)
RE_FILE_ID = re.compile(r"fuckingfast\.co/([^#/?]+)")
RE_FITGIRL_URL = re.compile(
    r"^https?://(?:www\.)?fitgirl-repacks\.site/[a-zA-Z0-9\-_]+(?:/[a-zA-Z0-9\-_/]*)?/?$",
    re.IGNORECASE,
)
RE_EXTRACT_LINK = re.compile(
    r'https?://(?:[a-zA-Z0-9-]+\.)*fuckingfast\.co(?:/[^\s"\'<>]*)?'
)
RE_RATE_LIMIT = re.compile(r"part(\d+)", re.IGNORECASE)

# ---------------------------------------------------------------------------
# Browser detection paths
# ---------------------------------------------------------------------------
BROWSER_PATHS: dict[str, list[str]] = {
    "Chrome": [
        r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
        r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
        r"%LocalAppData%\Google\Chrome\Application\chrome.exe",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ],
    "Edge": [
        r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
        r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe",
        r"%LocalAppData%\Microsoft\Edge\Application\msedge.exe",
        "/usr/bin/microsoft-edge",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    ],
    "Brave": [
        r"%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"%ProgramFiles(x86)%\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"%LocalAppData%\BraveSoftware\Brave-Browser\Application\brave.exe",
        "/usr/bin/brave-browser",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    ],
    "Chromium": [
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
    ],
}

# ---------------------------------------------------------------------------
# Zendriver / browser automation
# ---------------------------------------------------------------------------
ZENDRIVER_CF_VERIFY_TIMEOUT = 20
ZENDRIVER_CF_VERIFY_CLICK_DELAY = 1
# Max time (ms) to wait on the page for the Turnstile token to appear, and
# how often (ms) to re-check the token input while waiting.
ZENDRIVER_TURNSTILE_TOKEN_TIMEOUT_MS = 30000
ZENDRIVER_TURNSTILE_TOKEN_POLL_MS = 500
ZENDRIVER_BROWSER_ARGS = [
    "--window-size=500,175",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-extensions",
    "--disable-sync",
    "--disable-background-networking",
    "--disable-popup-blocking",
]
# Vertical gap (px) between stacked extraction windows; also the fallback
# window size parsed from --window-size when that flag is missing.
ZENDRIVER_WINDOW_GAP = 5
ZENDRIVER_WINDOW_DEFAULT_WIDTH = 500
ZENDRIVER_WINDOW_DEFAULT_HEIGHT = 175

# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------
FITGIRL_SEARCH_URL = "https://fitgirl-repacks.site/"
