"""High-level browser management facade."""

from __future__ import annotations

from ..config import ConfigManager
from .browser_detector import BrowserDetector


class BrowserManager:
    """Combines detection and selection into a single API."""

    def __init__(self, config: ConfigManager) -> None:
        self._config = config

    def get_available_browsers(self) -> dict[str, str]:
        """Return ``{name: path}`` for all detected browsers."""
        return BrowserDetector.find_all_browsers()

    def get_browser_path(self, name: str | None = None) -> str | None:
        """Return the executable path for the given (or selected) browser."""
        if name:
            return BrowserDetector.get_browser_path(name)
        selected = self._config.selected_browser
        if selected:
            return BrowserDetector.get_browser_path(selected)
        return BrowserDetector.detect_default_browser()

    def get_selected_browser_name(self) -> str | None:
        """Return the user-selected browser name, or ``None`` for auto."""
        return self._config.selected_browser
