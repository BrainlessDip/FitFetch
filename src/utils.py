"""Shared helper functions with no Qt dependencies."""

from __future__ import annotations

from urllib.parse import unquote

from .constants import RE_PART_NUM


def extract_filename(url: str) -> str:
    """Extract the filename from a URL, stripping any fragment."""
    return url.split("/")[-1].split("#")[-1]


def extract_hash_part(url: str) -> str:
    """Extract the part/file name from a URL's fragment (``#...``).

    Falls back to the last path segment when there is no fragment, and
    URL-decodes the value so encoded names still match.
    """
    if "#" in url:
        return unquote(url.split("#", 1)[1])
    return unquote(url.split("/")[-1])


def extract_part_num(filename: str) -> str:
    """Extract the part number string from *filename*, or ``'0'``."""
    m = RE_PART_NUM.search(filename)
    return m.group(1) if m else "0"
