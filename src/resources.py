"""PyInstaller-compatible resource path resolution."""

from __future__ import annotations

import sys
from pathlib import Path


def resource_path(relative_path: str) -> Path:
    """Return the absolute path to a resource file.

    Works both in development and when bundled by PyInstaller.

    Args:
        relative_path: Path relative to the project root or ``sys._MEIPASS``.

    Returns:
        Absolute ``Path`` to the resource.
    """
    if getattr(sys, "frozen", False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).resolve().parent.parent
    return base_path / relative_path
