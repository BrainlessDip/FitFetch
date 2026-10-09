"""Parse FitGirl search-results HTML into structured data."""

from __future__ import annotations

from ..models.data_models import FitGirlPagination, FitGirlSearchResult


class FitGirlParser:
    """Parses FitGirl search results page HTML."""

    @staticmethod
    def parse_search_results(
        html: str,
    ) -> tuple[list[FitGirlSearchResult], FitGirlPagination]:
        """Return ``(results, pagination)`` parsed from *html*."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        results: list[FitGirlSearchResult] = []

        for article in soup.find_all("article"):
            try:
                result = FitGirlParser._parse_article(article)
                if result:
                    results.append(result)
            except Exception:
                continue

        pagination = FitGirlParser._parse_pagination(soup)
        return results, pagination

    @staticmethod
    def _parse_article(article) -> FitGirlSearchResult | None:
        title_el = article.select_one(".entry-title a")
        if not title_el:
            return None

        title = title_el.get_text(strip=True)
        url = title_el.get("href", "")
        if not url:
            return None

        date = ""
        time_el = article.select_one(".entry-date time")
        if time_el:
            date = time_el.get_text(strip=True)
        elif article.select_one("time"):
            date = article.select_one("time").get_text(strip=True)

        cats: list[str] = []
        for cat_span in article.select(".cat-links"):
            for a in cat_span.select("a"):
                text = a.get_text(strip=True)
                if text:
                    cats.append(text)
        category = ", ".join(dict.fromkeys(cats))

        summary = ""
        summary_el = article.select_one(".entry-summary")
        if summary_el:
            summary = summary_el.get_text(strip=True)

        comments = None
        comment_el = article.select_one(".comments-link a, .comment-count")
        if comment_el:
            comments = comment_el.get_text(strip=True)

        tags: list[str] = []
        for tag_el in article.select(".tags-links a, .tag-links a"):
            tag_text = tag_el.get_text(strip=True)
            if tag_text:
                tags.append(tag_text)

        return FitGirlSearchResult(
            title=title,
            url=url,
            date=date,
            category=category,
            summary=summary,
            comments=comments,
            tags=tags,
        )

    @staticmethod
    def _parse_pagination(soup) -> FitGirlPagination:
        pagination = FitGirlPagination()
        nav = soup.select_one("div.pagination.loop-pagination")
        if not nav:
            return pagination

        current_el = nav.select_one("span.page-numbers.current")
        if current_el:
            try:
                pagination.current_page = int(current_el.get_text(strip=True))
            except ValueError, TypeError:
                pass

        page_links = nav.select("a.page-numbers:not(.next):not(.prev)")
        max_page = pagination.current_page
        for link in page_links:
            text = link.get_text(strip=True)
            try:
                num = int(text)
                if num > max_page:
                    max_page = num
            except ValueError, TypeError:
                pass
        pagination.total_pages = max_page

        next_el = nav.select_one("a.next.page-numbers")
        if next_el:
            pagination.next_url = next_el.get("href", "")

        prev_el = nav.select_one("a.prev.page-numbers")
        if prev_el:
            pagination.prev_url = prev_el.get("href", "")

        return pagination
