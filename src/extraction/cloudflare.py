"""Cloudflare-protected page fetching with httpx."""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

from ..constants import CF_TIMEOUT, MAX_CF_THREADS
from ..logger import logger

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/153.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
}

RETRY_STATUSES = frozenset({500, 502, 503, 504})
MAX_RETRIES = 5
BACKOFF_FACTOR = 1.5


class CloudflareBypass:
    """Handles Cloudflare-protected pages with httpx and retry strategy."""

    def __init__(self, threads: int = MAX_CF_THREADS) -> None:
        self.threads = threads
        self.local = threading.local()

    def _create_client(self) -> httpx.Client:
        return httpx.Client(
            headers=HEADERS,
            timeout=CF_TIMEOUT,
            transport=httpx.HTTPTransport(retries=3),
        )

    def _get_client(self) -> httpx.Client:
        if not hasattr(self.local, "client"):
            self.local.client = self._create_client()
        return self.local.client

    def fetch(
        self, url: str, method: str = "GET"
    ) -> tuple[str, str | None, int | None, httpx.Headers | None]:
        """Fetch a single URL. Returns ``(url, text, status_code, headers)``."""
        client = self._get_client()
        try:
            for attempt in range(MAX_RETRIES):
                if method == "GET":
                    r = client.get(url, follow_redirects=True)
                else:
                    r = client.post(url, follow_redirects=False)
                if r.status_code not in RETRY_STATUSES or attempt >= MAX_RETRIES - 1:
                    break
                time.sleep(BACKOFF_FACTOR * (attempt + 1))
            return url, r.text, r.status_code, r.headers
        except (httpx.HTTPError, httpx.InvalidURL) as exc:
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
