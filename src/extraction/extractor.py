"""High-level extraction orchestrator (stub for future expansion)."""

from __future__ import annotations

from .engines import ExtractionEngine


def select_engine(method: str) -> ExtractionEngine:
    """Map a method string (``'v1'``/``'v2'``) to an :class:`ExtractionEngine`."""
    if method == "v2":
        return ExtractionEngine.BROWSER
    return ExtractionEngine.CLOUDFLARE
