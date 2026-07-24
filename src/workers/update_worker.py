"""Background worker for GitHub update checks."""

from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal

from ..logger import logger
from ..services.github_service import GitHubService


class CheckUpdateWorker(QThread):
    """Check GitHub for the latest release in a background thread."""

    update_found = pyqtSignal(str, str, str, str, str)
    update_error = pyqtSignal(str)
    no_update = pyqtSignal(str, str, str, str)

    def __init__(
        self, owner: str, repo: str, current_version: str, parent=None
    ) -> None:
        super().__init__(parent)
        self.owner = owner
        self.repo = repo
        self.current_version = current_version

    def run(self) -> None:
        try:
            data = GitHubService.get_latest_release(
                self.owner, self.repo, self.current_version
            )
        except ConnectionError:
            self.update_error.emit("Could not connect to GitHub. Check your internet.")
            return
        except TimeoutError:
            self.update_error.emit("GitHub request timed out. Try again later.")
            return
        except ValueError as exc:
            self.update_error.emit(str(exc))
            return

        if data is None:
            self.update_error.emit("No data received from GitHub.")
            return

        tag = data["tag"]
        if GitHubService.is_newer(tag, self.current_version):
            self.update_found.emit(
                tag,
                data["body"],
                data["html_url"],
                data["published_at"],
                data["download_url"],
            )
        else:
            self.no_update.emit(
                tag, data["body"], data["html_url"], data["published_at"]
            )
