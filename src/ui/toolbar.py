"""Toolbar factory for the main window."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QToolBar

from .styles import ModernStyle

if TYPE_CHECKING:
    from .main_window import FitFetchApp


def create_toolbar(window: FitFetchApp) -> QToolBar:
    """Build and attach the application toolbar to *window*."""
    toolbar = QToolBar("Main Toolbar", window)
    toolbar.setObjectName("mainToolBar")
    toolbar.setMovable(False)
    toolbar.setFloatable(False)
    toolbar.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
    toolbar.setStyleSheet(ModernStyle.toolbar_style())
    window.addToolBar(toolbar)

    explorer_btn = QAction("Explorer", window)
    explorer_btn.triggered.connect(lambda: window._switch_page(1))
    toolbar.addAction(explorer_btn)

    extractor_btn = QAction("Extractor", window)
    extractor_btn.triggered.connect(lambda: window._switch_page(0))
    toolbar.addAction(extractor_btn)

    extract_v1_btn = QAction("Extract V1", window)
    extract_v1_btn.triggered.connect(lambda: window.start_extraction(method="v1"))
    toolbar.addAction(extract_v1_btn)

    extract_v2_btn = QAction("Extract V2", window)
    extract_v2_btn.triggered.connect(lambda: window.start_extraction(method="v2"))
    toolbar.addAction(extract_v2_btn)

    toolbar.addSeparator()

    select_all_btn = QAction("Select All", window)
    select_all_btn.triggered.connect(window.select_all)
    toolbar.addAction(select_all_btn)

    deselect_all_btn = QAction("Deselect All", window)
    deselect_all_btn.triggered.connect(window.deselect_all)
    toolbar.addAction(deselect_all_btn)

    toolbar.addSeparator()

    save_btn = QAction("Save", window)
    save_btn.triggered.connect(window.save_links)
    toolbar.addAction(save_btn)

    copy_btn = QAction("Copy", window)
    copy_btn.triggered.connect(window.copy_output)
    toolbar.addAction(copy_btn)

    clear_btn = QAction("Clear", window)
    clear_btn.triggered.connect(window.clear_output)
    toolbar.addAction(clear_btn)

    return toolbar
