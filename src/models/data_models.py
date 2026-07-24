"""Plain data containers used across FitFetch."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FitGirlSearchResult:
    """A single search result from FitGirl Repacks."""

    title: str
    url: str
    date: str
    category: str
    summary: str
    comments: str | None = None
    tags: list[str] = field(default_factory=list)


@dataclass
class FitGirlPagination:
    """Pagination metadata from a FitGirl search results page."""

    current_page: int = 1
    total_pages: int = 1
    next_url: str | None = None
    prev_url: str | None = None
