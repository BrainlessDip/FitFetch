"""FitGirl repack page fetching service."""

from __future__ import annotations

import re as _re

from ..constants import CF_TIMEOUT, DEFAULT_USER_AGENT


class FitGirlService:
    """Fetches a FitGirl repack page and extracts download links."""

    @staticmethod
    def fetch_links(url: str) -> tuple[list[str], str]:
        """Fetch *url* and return ``(links, size_info)``.

        Raises:
            Exception: On network or parsing errors.
        """
        import cloudscraper
        from bs4 import BeautifulSoup

        scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )
        scraper.headers.update({"User-Agent": DEFAULT_USER_AGENT})

        html = scraper.get(url, timeout=CF_TIMEOUT).text
        soup = BeautifulSoup(html, "html.parser")

        links = list(
            {
                a["href"]
                for a in soup.find_all("a", href=True)
                if "fuckingfast.co" in a["href"]
            }
        )

        size_pattern = _re.compile(
            r"(Original Size|Repack Size)\s*:\s*(from\s+)?([\d.]+(?:\s*/\s*[\d.]+)?\s*\w+)",
            _re.IGNORECASE,
        )
        sizes: list[str] = []
        for label, prefix, value in size_pattern.findall(html):
            sizes.append(f"{label}: {prefix or ''}{value}")
        size_info = " | ".join(sizes) if sizes else ""

        return links, size_info
