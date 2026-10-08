"""FitGirl search service."""

from __future__ import annotations

import time

import httpx

from ..constants import DEFAULT_USER_AGENT, FITGIRL_SEARCH_URL, REQUEST_TIMEOUT
from ..extraction.parser import FitGirlParser
from ..models.data_models import FitGirlPagination, FitGirlSearchResult

SEARCH_HEADERS = {
    "User-Agent": DEFAULT_USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "en-US,en;q=0.9",
}
SEARCH_RETRY_STATUSES = frozenset({500, 502, 503, 504})
SEARCH_MAX_RETRIES = 2
SEARCH_BACKOFF_FACTOR = 0.5


class SearchService:
    """Performs FitGirl site searches and returns structured results."""

    @staticmethod
    def search(
        query: str, page: int = 1
    ) -> tuple[list[FitGirlSearchResult], FitGirlPagination]:
        """Search FitGirl and return ``(results, pagination)``.

        Raises:
            httpx.HTTPError: No internet, timeout, or HTTP error status.
        """
        params = {"s": query}
        url = f"{FITGIRL_SEARCH_URL}page/{page}/" if page > 1 else FITGIRL_SEARCH_URL

        with httpx.Client(
            headers=SEARCH_HEADERS,
            timeout=REQUEST_TIMEOUT,
            transport=httpx.HTTPTransport(retries=SEARCH_MAX_RETRIES),
            follow_redirects=True,
        ) as client:
            resp = client.get(url, params=params)
            attempt = 0
            # httpx's transport-level retries only cover connection failures,
            # so retryable HTTP statuses are handled here.
            while (
                resp.status_code in SEARCH_RETRY_STATUSES
                and attempt < SEARCH_MAX_RETRIES
            ):
                time.sleep(SEARCH_BACKOFF_FACTOR * (attempt + 1))
                attempt += 1
                resp = client.get(url, params=params)

            resp.raise_for_status()
            return FitGirlParser.parse_search_results(resp.text)
