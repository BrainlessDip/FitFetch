"""Shared helper functions with no Qt dependencies."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

from .constants import (
    RE_FF_URL,
    RE_FILE_ID,
    RE_PART_NUM,
    RE_URL_LOOSE,
    UNKNOWN_FILENAME,
)


@dataclass(frozen=True)
class LinkScan:
    """Result of scanning pasted text for FuckingFast links."""

    links: list[str]
    duplicates: int
    invalid: int


def extract_filename(url: str) -> str:
    """Extract the filename from a URL, stripping any fragment."""
    return url.split("/")[-1].split("#")[-1]


def display_filename(url: str) -> str:
    """Return the human-readable file name shown in link lists.

    Falls back to :data:`~src.constants.UNKNOWN_FILENAME` when the URL has no
    ``#filename`` fragment, because a bare file id is not a name.
    """
    if "#" in url:
        return url.split("#", 1)[1] or UNKNOWN_FILENAME
    return UNKNOWN_FILENAME


def scan_links(text: str) -> LinkScan:
    """Scan arbitrary pasted *text* for FuckingFast links.

    Handles Markdown links, bare URLs, several links per line and surrounding
    prose. Returns the valid links with duplicates removed and their original
    order preserved, plus how many duplicates and non-FuckingFast URLs were
    ignored so the caller can report them.
    """
    text = text or ""
    links: list[str] = []
    seen: set[str] = set()
    duplicates = 0

    for match in RE_FF_URL.finditer(text):
        url = match.group(0).rstrip(".,;")
        if not RE_FILE_ID.search(url):
            continue
        if url in seen:
            duplicates += 1
            continue
        seen.add(url)
        links.append(url)

    invalid = len(
        {
            url
            for url in (m.group(0).rstrip(".,;") for m in RE_URL_LOOSE.finditer(text))
            if not RE_FILE_ID.search(url)
        }
    )

    return LinkScan(links=links, duplicates=duplicates, invalid=invalid)


def extract_hash_part(url: str) -> str:
    """Extract the part/file name from a URL's fragment (``#...``).

    Falls back to the last path segment when there is no fragment, and
    URL-decodes the value so encoded names still match.
    """
    if "#" in url:
        return unquote(url.split("#", 1)[1])
    return unquote(url.split("/")[-1])


def get_profiles_dir() -> Path:
    """Return the base directory that holds per-worker browser profiles."""
    return Path(tempfile.gettempdir()) / "FitFetch" / "profiles"


def get_worker_profile_dir(worker_index: int) -> Path:
    """Create and return the isolated profile dir for *worker_index*."""
    profile = get_profiles_dir() / f"worker_{worker_index}"
    profile.mkdir(parents=True, exist_ok=True)
    return profile


def remove_worker_profile_dir(worker_index: int) -> None:
    """Recursively remove the profile dir for *worker_index*.

    Failures are ignored so one worker's cleanup never affects others.
    """
    import shutil

    try:
        shutil.rmtree(get_worker_profile_dir(worker_index), ignore_errors=True)
    except Exception:
        pass


def extract_part_num(filename: str) -> str:
    """Extract the part number string from *filename*, or ``'0'``."""
    m = RE_PART_NUM.search(filename)
    return m.group(1) if m else "0"
