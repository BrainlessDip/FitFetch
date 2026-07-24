"""QApplication startup and main window launch."""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication, QStyleFactory
from PyQt6.QtGui import QIcon

from .constants import APP_NAME
from .resources import resource_path
from .ui.main_window import FitFetchApp


def run() -> int:
    """Create the application, show the main window, and run the event loop."""
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle(QStyleFactory.create("Fusion"))
    app.setWindowIcon(QIcon(str(resource_path("assets/favicon.ico"))))

    window = FitFetchApp()
    window.show()

    return app.exec()
