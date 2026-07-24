"""Extraction engine enumeration."""

from __future__ import annotations

from enum import Enum


class ExtractionEngine(Enum):
    """Supported extraction strategies."""

    CLOUDFLARE = "v1"
    BROWSER = "v2"
