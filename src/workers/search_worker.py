"""Background worker for FitGirl searches."""

from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal

from ..logger import logger
from ..services.search_service import SearchService


class FitGirlSearchWorker(QThread):
    """Perform a FitGirl search in a background thread."""

    results_ready = pyqtSignal(list, object)
    search_error = pyqtSignal(str)

    def __init__(self, query: str, page: int = 1, parent=None) -> None:
        super().__init__(parent)
        self.query = query
        self.page = page

    def run(self) -> None:
        try:
            results, pagination = SearchService.search(self.query, self.page)
            self.results_ready.emit(results, pagination)
        except Exception as exc:
            logger.exception("FitGirlSearchWorker error")
            self.search_error.emit(f"Search failed: {exc}")
