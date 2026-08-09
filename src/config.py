"""Centralised configuration management via QSettings.

Wraps :class:`QSettings` with typed accessors so that every
preference is read and written through a single, testable API.
"""

from __future__ import annotations

from PyQt6.QtCore import QByteArray, QSettings

from .constants import APP_NAME

# Number of parallel V2 extraction browser windows (also = profile count).
DEFAULT_WINDOW_COUNT = 1
MIN_WINDOW_COUNT = 1
MAX_WINDOW_COUNT = 8


class ConfigManager:
    """Typed wrapper around :class:`QSettings` for FitFetch."""

    def __init__(self) -> None:
        self._settings = QSettings(APP_NAME, "AppData")

    # -- Extraction delays ---------------------------------------------------

    @property
    def v1_delay(self) -> int:
        """Delay (ms) between V1 (Cloudflare) requests."""
        return int(self._settings.value("delays/v1", 0, type=int))

    @v1_delay.setter
    def v1_delay(self, value: int) -> None:
        self._settings.setValue("delays/v1", value)

    @property
    def v2_delay(self) -> int:
        """Delay (ms) between V2 (Browser) requests."""
        return int(self._settings.value("delays/v2", 0, type=int))

    @v2_delay.setter
    def v2_delay(self, value: int) -> None:
        self._settings.setValue("delays/v2", value)

    # -- Multi-window settings -----------------------------------------------

    @property
    def window_count(self) -> int:
        """Number of parallel V2 extraction browser windows (default: 2)."""
        return int(
            self._settings.value(
                "extraction/window_count", DEFAULT_WINDOW_COUNT, type=int
            )
        )

    @window_count.setter
    def window_count(self, value: int) -> None:
        self._settings.setValue("extraction/window_count", int(value))

    @property
    def random_window_positions(self) -> bool:
        """Whether V2 browser windows spawn at random screen positions."""
        return bool(
            self._settings.value("extraction/random_window_positions", False, type=bool)
        )

    @random_window_positions.setter
    def random_window_positions(self, value: bool) -> None:
        self._settings.setValue("extraction/random_window_positions", bool(value))

    # -- Browser selection ---------------------------------------------------

    @property
    def selected_browser(self) -> str | None:
        """Name of the selected browser (``None`` = auto-detect)."""
        val = self._settings.value("browser/selected", None)
        return str(val) if val else None

    @selected_browser.setter
    def selected_browser(self, value: str | None) -> None:
        if value is None:
            self._settings.remove("browser/selected")
        else:
            self._settings.setValue("browser/selected", value)

    # -- Window geometry / state ---------------------------------------------

    def save_window_geometry(self, geometry: QByteArray) -> None:
        self._settings.setValue("window/geometry", geometry)

    def load_window_geometry(self) -> QByteArray | None:
        val = self._settings.value("window/geometry")
        return val if isinstance(val, QByteArray) else None

    def save_window_state(self, state: QByteArray) -> None:
        self._settings.setValue("window/state", state)

    def load_window_state(self) -> QByteArray | None:
        val = self._settings.value("window/state")
        return val if isinstance(val, QByteArray) else None
