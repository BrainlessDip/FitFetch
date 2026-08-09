"""FitGirl search service."""

from __future__ import annotations

from ..constants import DEFAULT_USER_AGENT, FITGIRL_SEARCH_URL, REQUEST_TIMEOUT
from ..extraction.parser import FitGirlParser
from ..models.data_models import FitGirlPagination, FitGirlSearchResult


class SearchService:
    """Performs FitGirl site searches and returns structured results."""

    @staticmethod
    def search(
        query: str, page: int = 1
    ) -> tuple[list[FitGirlSearchResult], FitGirlPagination]:
        """Search FitGirl and return ``(results, pagination)``.

        Raises:
            ConnectionError: No internet.
            Timeout: Server slow/offline.
            ValueError: HTTP errors.
        """
        import requests as _requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        session = _requests.Session()
        session.headers.update(
            {
                "User-Agent": DEFAULT_USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )
        retry = Retry(
            total=2, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        try:
            params = {"s": query}
            url = (
                f"{FITGIRL_SEARCH_URL}page/{page}/" if page > 1 else FITGIRL_SEARCH_URL
            )
            resp = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return FitGirlParser.parse_search_results(resp.text)
        finally:
            session.close()
