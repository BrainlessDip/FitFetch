"""FitGirl Repacks search explorer widget."""

from __future__ import annotations

import re

from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..models.data_models import FitGirlPagination, FitGirlSearchResult
from ..workers.search_worker import FitGirlSearchWorker
from .styles import ModernStyle
from .widgets import ModernGroupBox


class FitGirlExplorerWidget(QWidget):
    """Built-in FitGirl Repacks search explorer."""

    send_to_extractor = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._search_worker = None
        self._current_query = ""
        self._current_page = 1
        self._pagination = FitGirlPagination()
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        # Search bar
        search_group = ModernGroupBox("Search FitGirl Repacks")
        search_layout = QHBoxLayout(search_group)
        search_layout.setSpacing(8)
        search_layout.setContentsMargins(10, 8, 10, 10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Search for games... (e.g. GTA, Cyberpunk, Elden Ring)"
        )
        self.search_input.returnPressed.connect(self._on_search)
        search_layout.addWidget(self.search_input)

        self.search_btn = QPushButton("Search")
        self.search_btn.setFixedWidth(90)
        self.search_btn.setFixedHeight(32)
        self.search_btn.clicked.connect(self._on_search)
        search_layout.addWidget(self.search_btn)

        layout.addWidget(search_group)

        # Status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(
            f"color: {ModernStyle.TEXT_SECONDARY}; font-size: 11px; padding: 2px 4px;"
        )
        layout.addWidget(self.status_label)

        # Results scroll area
        self.results_scroll = QScrollArea()
        self.results_scroll.setWidgetResizable(True)
        self.results_scroll.setStyleSheet(
            "QScrollArea { border: none; background-color: transparent; }"
        )

        self.results_container = QWidget()
        self.results_container.setStyleSheet(
            f"background-color: {ModernStyle.BG_PRIMARY};"
        )
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.results_layout.setSpacing(8)
        self.results_layout.setContentsMargins(4, 4, 4, 4)

        self.results_scroll.setWidget(self.results_container)
        layout.addWidget(self.results_scroll)

        # Pagination bar
        self._pagination_bar = QWidget()
        self._pagination_bar.setStyleSheet(f"""
            QWidget {{
                background-color: {ModernStyle.BG_SECONDARY};
                border: 1px solid {ModernStyle.BORDER};
                border-radius: {ModernStyle.RADIUS}px;
            }}
        """)
        pag_layout = QHBoxLayout(self._pagination_bar)
        pag_layout.setContentsMargins(12, 6, 12, 6)
        pag_layout.setSpacing(8)

        pag_btn_style = f"""
            QPushButton {{
                background-color: {ModernStyle.BG_TERTIARY};
                color: {ModernStyle.TEXT_PRIMARY};
                border: 1px solid {ModernStyle.BORDER};
                border-radius: 6px;
                padding: 4px 14px;
                font-size: 11px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {ModernStyle.BG_HOVER};
                border-color: {ModernStyle.BORDER_ACTIVE};
            }}
            QPushButton:pressed {{
                background-color: {ModernStyle.BG_ACTIVE};
                padding-top: 5px;
                padding-bottom: 3px;
            }}
            QPushButton:disabled {{
                color: {ModernStyle.TEXT_MUTED};
                background-color: {ModernStyle.BG_SECONDARY};
                border-color: {ModernStyle.BORDER};
            }}
        """

        self._prev_btn = QPushButton("\u2190 Prev")
        self._prev_btn.setStyleSheet(pag_btn_style)
        self._prev_btn.setFixedHeight(28)
        self._prev_btn.clicked.connect(self._on_prev_page)
        pag_layout.addWidget(self._prev_btn)

        self._page_input = QLineEdit()
        self._page_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._page_input.setFixedWidth(110)
        self._page_input.setFixedHeight(28)
        self._page_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {ModernStyle.BG_TERTIARY};
                color: {ModernStyle.TEXT_PRIMARY};
                border: 1px solid {ModernStyle.BORDER};
                border-radius: 6px;
                padding: 2px 6px;
                font-size: 11px;
                font-weight: 500;
            }}
            QLineEdit:focus {{
                border-color: {ModernStyle.ACCENT};
            }}
        """)
        self._page_input.returnPressed.connect(self._on_page_submit)
        self._page_input.installEventFilter(self)
        pag_layout.addWidget(self._page_input)

        self._next_btn = QPushButton("Next \u2192")
        self._next_btn.setStyleSheet(pag_btn_style)
        self._next_btn.setFixedHeight(28)
        self._next_btn.clicked.connect(self._on_next_page)
        pag_layout.addWidget(self._next_btn)

        self._pagination_bar.setVisible(False)
        layout.addWidget(self._pagination_bar)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def _on_search(self) -> None:
        query = self.search_input.text().strip()
        if not query:
            return
        if self._search_worker and self._search_worker.isRunning():
            return
        self._current_query = query
        self._current_page = 1
        self._start_search(query, 1)

    def _on_prev_page(self) -> None:
        if self._current_page > 1 and self._current_query:
            self._current_page -= 1
            self._start_search(self._current_query, self._current_page)

    def _on_next_page(self) -> None:
        if self._current_page < self._pagination.total_pages and self._current_query:
            self._current_page += 1
            self._start_search(self._current_query, self._current_page)

    def _start_search(self, query: str, page: int) -> None:
        if self._search_worker and self._search_worker.isRunning():
            return

        self.search_btn.setEnabled(False)
        self._prev_btn.setEnabled(False)
        self._next_btn.setEnabled(False)
        self.status_label.setText(f"Searching page {page}...")
        self._clear_results()

        self._search_worker = FitGirlSearchWorker(query, page)
        self._search_worker.results_ready.connect(self._on_results)
        self._search_worker.search_error.connect(self._on_error)
        self._search_worker.finished.connect(self._on_worker_finished)
        self._search_worker.start()

    def _on_worker_finished(self) -> None:
        self.search_btn.setEnabled(True)
        self._update_pagination_ui()
        self._search_worker = None

    def _on_results(
        self, results: list[FitGirlSearchResult], pagination: FitGirlPagination
    ) -> None:
        self._pagination = pagination
        if not results:
            self.status_label.setText("No results found.")
            return

        page_info = (
            f" (page {pagination.current_page}/{pagination.total_pages})"
            if pagination.total_pages > 1
            else ""
        )
        self.status_label.setText(f"Found {len(results)} result(s){page_info}")
        for result in results:
            card = self._create_result_card(result)
            self.results_layout.addWidget(card)

    def _on_error(self, message: str) -> None:
        self.status_label.setText(f"Error: {message}")

    def eventFilter(self, obj, event) -> bool:
        if obj is self._page_input:
            if event.type() == event.Type.FocusIn:
                self._page_input.clear()
            elif event.type() == event.Type.FocusOut:
                self._on_page_submit()
        return super().eventFilter(obj, event)

    def _update_pagination_ui(self) -> None:
        pag = self._pagination
        if pag.total_pages <= 1:
            self._pagination_bar.setVisible(False)
            return
        self._pagination_bar.setVisible(True)
        self._page_input.setText(f"Page {pag.current_page} of {pag.total_pages}")
        self._prev_btn.setEnabled(pag.current_page > 1)
        self._next_btn.setEnabled(pag.current_page < pag.total_pages)

    def _on_page_submit(self) -> None:
        text = self._page_input.text().strip()
        match = re.search(r"(\d+)", text)
        if not match:
            self._page_input.setText(
                f"Page {self._pagination.current_page} of {self._pagination.total_pages}"
            )
            return

        page = int(match.group(1))
        if page < 1 or page > self._pagination.total_pages:
            self._page_input.setText(
                f"Page {self._pagination.current_page} of {self._pagination.total_pages}"
            )
            return

        if page != self._pagination.current_page:
            self._current_page = page
            self._start_search(self._current_query, page)

    def _clear_results(self) -> None:
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    # ------------------------------------------------------------------
    # Result card
    # ------------------------------------------------------------------

    def _create_result_card(self, result: FitGirlSearchResult) -> QWidget:
        card = QWidget()
        card.setObjectName("resultCard")
        card.setStyleSheet(f"""
            QWidget#resultCard {{
                background-color: {ModernStyle.BG_SECONDARY};
                border: 1px solid {ModernStyle.BORDER};
                border-left: 3px solid {ModernStyle.ACCENT};
                border-radius: {ModernStyle.RADIUS}px;
            }}
            QWidget#resultCard:hover {{
                border-color: {ModernStyle.BORDER_ACTIVE};
                border-left-color: {ModernStyle.ACCENT_HOVER};
                background-color: #1a2233;
            }}
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(8)
        card_layout.setContentsMargins(14, 12, 14, 12)

        # Top row
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        title_col = QVBoxLayout()
        title_col.setSpacing(4)

        title_label = QLabel(result.title)
        title_label.setStyleSheet(f"""
            QLabel {{
                background: transparent;
                font-size: 14px;
                font-weight: 700;
                color: {ModernStyle.TEXT_PRIMARY};
            }}
        """)
        title_label.setWordWrap(True)
        title_col.addWidget(title_label)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(8)

        if result.category:
            for cat in [c.strip() for c in result.category.split(",") if c.strip()]:
                badge = QLabel(cat)
                badge.setStyleSheet(f"""
                    QLabel {{
                        background-color: rgba(59, 130, 246, 0.15);
                        color: {ModernStyle.ACCENT};
                        border: 1px solid rgba(59, 130, 246, 0.3);
                        border-radius: 4px;
                        padding: 2px 8px;
                        font-size: 10px;
                        font-weight: 600;
                    }}
                """)
                badge.setFixedHeight(20)
                meta_row.addWidget(badge)

        if result.date:
            date_label = QLabel(result.date)
            date_label.setStyleSheet(f"""
                QLabel {{
                    background: transparent;
                    color: {ModernStyle.TEXT_MUTED};
                    font-size: 11px;
                }}
            """)
            meta_row.addWidget(date_label)

        if result.comments:
            comment_label = QLabel(result.comments)
            comment_label.setStyleSheet(f"""
                QLabel {{
                    background: transparent;
                    color: {ModernStyle.TEXT_MUTED};
                    font-size: 10px;
                }}
            """)
            meta_row.addWidget(comment_label)

        meta_row.addStretch()
        title_col.addLayout(meta_row)
        top_row.addLayout(title_col, 1)
        card_layout.addLayout(top_row)

        # Buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        card_btn_style = ModernStyle.card_button_style()

        extract_btn = QPushButton("Extract")
        extract_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ModernStyle.ACCENT_PRESSED};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 5px 18px;
                font-size: 11px;
                font-weight: 600;
                min-width: 60px;
            }}
            QPushButton:hover {{
                background-color: {ModernStyle.ACCENT};
            }}
            QPushButton:pressed {{
                background-color: #153DAB;
                padding-top: 6px;
                padding-bottom: 4px;
            }}
        """)
        extract_btn.setFixedHeight(28)
        extract_btn.clicked.connect(lambda _, r=result: self._on_extract(r))
        btn_row.addWidget(extract_btn)

        browser_btn = QPushButton("Open Website")
        browser_btn.setStyleSheet(card_btn_style)
        browser_btn.setFixedHeight(28)
        browser_btn.clicked.connect(lambda _, r=result: self._on_open_website(r))
        btn_row.addWidget(browser_btn)

        btn_row.addStretch()
        card_layout.addLayout(btn_row)

        return card

    def _on_extract(self, result: FitGirlSearchResult) -> None:
        self.send_to_extractor.emit(result.url)

    def _on_open_website(self, result: FitGirlSearchResult) -> None:
        QDesktopServices.openUrl(QUrl(result.url))
