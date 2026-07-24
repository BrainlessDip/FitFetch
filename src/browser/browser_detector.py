"""Detect installed Chromium-based browsers on the system."""

from __future__ import annotations

import os

from ..constants import BROWSER_PATHS


class BrowserDetector:
    """Detects installed Chromium-based browsers on the system."""

    @classmethod
    def find_all_browsers(cls) -> dict[str, str]:
        """Return ``{name: path}`` for every installed browser found."""
        found: dict[str, str] = {}
        for name, paths in BROWSER_PATHS.items():
            for path_template in paths:
                path = os.path.expandvars(path_template)
                if os.path.isfile(path):
                    found[name] = path
                    break
        return found

    @classmethod
    def detect_default_browser(cls) -> str | None:
        """Return the path of the first available browser, or ``None``."""
        browsers = cls.find_all_browsers()
        return next(iter(browsers.values())) if browsers else None

    @classmethod
    def get_browser_path(cls, name: str) -> str | None:
        """Return the executable path for *name*, or ``None``."""
        return cls.find_all_browsers().get(name)
