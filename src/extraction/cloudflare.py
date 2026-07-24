"""Cloudflare-protected page fetching with cloudscraper."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..constants import CF_TIMEOUT, DEFAULT_USER_AGENT, MAX_CF_THREADS
from ..logger import logger


class CloudflareBypass:
    """Handles Cloudflare-protected pages with cloudscraper and retry strategy."""

    def __init__(self, threads: int = MAX_CF_THREADS) -> None:
        self.threads = threads
        self.local = threading.local()

    def _create_session(self):
        import cloudscraper
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )
        scraper.headers.update({"User-Agent": DEFAULT_USER_AGENT})
        retry_strategy = Retry(
            total=5,
            backoff_factor=1.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(
            max_retries=retry_strategy, pool_connections=100, pool_maxsize=100
        )
        scraper.mount("http://", adapter)
        scraper.mount("https://", adapter)
        return scraper

    def _get_session(self):
        if not hasattr(self.local, "session"):
            self.local.session = self._create_session()
        return self.local.session

    def fetch(self, url: str, method: str = "GET"):
        """Fetch a single URL. Returns ``(url, text, status_code, headers)``."""
        session = self._get_session()
        try:
            r = (
                session.get(url, timeout=CF_TIMEOUT, allow_redirects=True)
                if method == "GET"
                else session.post(url, timeout=CF_TIMEOUT, allow_redirects=False)
            )
            return url, r.text, r.status_code, r.headers
        except Exception as exc:
            logger.debug("Fetch failed for %s: %s", url, exc)
            return url, None, None, None

    def fetch_many(self, urls: list[str]) -> dict:
        """Fetch multiple URLs concurrently."""
        results: dict = {}
        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            futures = {executor.submit(self.fetch, url): url for url in urls}
            for f in as_completed(futures):
                url, data, status, headers = f.result()
                results[url] = {
                    "content": data,
                    "status": status,
                    "url": url,
                    "headers": headers,
                }
        return results
