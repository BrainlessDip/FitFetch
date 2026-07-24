"""Background worker for fetching FitGirl repack pages."""

from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal

from ..logger import logger
from ..services.fitgirl_service import FitGirlService


class FitGirlFetchWorker(QThread):
    """Fetch links from a FitGirl page in a background thread."""

    status_update = pyqtSignal(str)
    fetch_complete = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    size_info = pyqtSignal(str)

    def __init__(self, url: str, parent=None) -> None:
        super().__init__(parent)
        self.url = url

    def run(self) -> None:
        try:
            self.status_update.emit("Fetching links from FitGirl...")
            links, sizes = FitGirlService.fetch_links(self.url)
            if sizes:
                self.size_info.emit(sizes)
            self.fetch_complete.emit(links)
        except Exception as exc:
            logger.exception("FitGirlFetchWorker error")
            self.error_occurred.emit(f"Fetch error: {exc}")
