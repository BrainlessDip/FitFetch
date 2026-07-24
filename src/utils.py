"""Shared helper functions with no Qt dependencies."""

from __future__ import annotations

from .constants import RE_PART_NUM


def extract_filename(url: str) -> str:
    """Extract the filename from a URL, stripping any fragment."""
    return url.split("/")[-1].split("#")[-1]


def extract_part_num(filename: str) -> str:
    """Extract the part number string from *filename*, or ``'0'``."""
    m = RE_PART_NUM.search(filename)
    return m.group(1) if m else "0"
