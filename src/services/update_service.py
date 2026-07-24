"""Update management service."""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal

from ..constants import APP_NAME, OWNER, VERSION
from ..logger import logger
from .github_service import GitHubService


class UpdateManager(QObject):
    """Orchestrates background and manual update checks.

    Signals:
        update_available(tag, body, html_url, published_at, download_url)
        check_failed(message)
        check_started()
        no_update_found(tag, body, html_url, published_at)
    """

    update_available = pyqtSignal(str, str, str, str, str)
    check_failed = pyqtSignal(str)
    check_started = pyqtSignal()
    no_update_found = pyqtSignal(str, str, str, str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._worker = None
        self._silent = True

    def check_for_updates(self, silent: bool = True) -> None:
        """Start an update check.

        Args:
            silent: If ``True``, only shows the update-available dialog.
        """
        if self._worker and self._worker.isRunning():
            return

        self._silent = silent
        self.check_started.emit()

        from ..workers.update_worker import CheckUpdateWorker

        self._worker = CheckUpdateWorker(OWNER, APP_NAME.lower(), VERSION)
        self._worker.update_found.connect(self._on_update_found)
        self._worker.update_error.connect(self._on_check_error)
        self._worker.no_update.connect(self._on_no_update)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def _on_worker_finished(self) -> None:
        self._worker = None

    def _on_update_found(
        self, tag: str, body: str, html_url: str, published_at: str, download_url: str
    ) -> None:
        self.update_available.emit(tag, body, html_url, published_at, download_url)

    def _on_check_error(self, message: str) -> None:
        if self._silent:
            return
        self.check_failed.emit(message)

    def _on_no_update(
        self, tag: str, body: str, html_url: str, published_at: str
    ) -> None:
        if self._silent:
            return
        self.no_update_found.emit(tag, body, html_url, published_at)
