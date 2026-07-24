"""Main application window for FitFetch."""

from __future__ import annotations

import os
import re
import sys
import time
from datetime import datetime

from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QAction, QDesktopServices, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..browser.browser_detector import BrowserDetector
from ..browser.browser_manager import BrowserManager
from ..config import ConfigManager
from ..constants import (
    APP_NAME,
    CLOSE_WAIT_MS,
    MAX_CF_THREADS,
    OWNER,
    RE_FITGIRL_URL,
    RE_PART_NUM,
    STARTUP_UPDATE_DELAY_MS,
    VERSION,
)
from ..logger import logger
from ..models.data_models import FitGirlPagination, FitGirlSearchResult
from ..services.update_service import UpdateManager
from ..utils import extract_filename, extract_part_num
from ..workers.extraction_worker import CloudflareWorker, ZendriverWorker
from ..workers.search_worker import FitGirlSearchWorker
from .dialogs import (
    AboutDialog,
    BrowserSettingsDialog,
    HelpDialog,
    SettingsDialog,
    VersionDialog,
)
from .explorer_widget import FitGirlExplorerWidget
from .file_selection_dialog import FileSelectionDialog
from .styles import ModernStyle
from .toolbar import create_toolbar
from .widgets import ClickableCheckBox


class FitFetchApp(QMainWindow):
    """FitFetch main window — builds UI, connects signals, displays results."""

    def __init__(self, config: ConfigManager | None = None) -> None:
        super().__init__()

        # Dependencies
        self._config = config or ConfigManager()
        self._browser_manager = BrowserManager(self._config)

        # State
        self.checkboxes: list[ClickableCheckBox] = []
        self.checkbox_links: dict[ClickableCheckBox, str] = {}
        self.checkbox_widgets: list[QWidget] = []
        self.links: list[str] = []
        self.current_file: str | None = None
        self.worker = None
        self.extract_worker = None
        self._fetched_size = ""
        self._fetch_start_time = 0.0
        self._extract_start_time = 0.0
        self._selected_browser: str | None = self._config.selected_browser
        self._startup_update_shown = False

        # Update manager
        self._update_manager = UpdateManager(self)
        self._update_manager.update_available.connect(self._on_update_found)
        self._update_manager.check_failed.connect(self._on_update_error)
        self._update_manager.no_update_found.connect(self._on_no_update)

        # Build UI
        self._init_ui()
        self.setStyleSheet(ModernStyle.application_style())
        self._restore_window_state()

    # ------------------------------------------------------------------
    # Window state persistence
    # ------------------------------------------------------------------

    def _restore_window_state(self) -> None:
        geom = self._config.load_window_geometry()
        if geom:
            self.restoreGeometry(geom)
        state = self._config.load_window_state()
        if state:
            self.restoreState(state)

    def closeEvent(self, event) -> None:
        if self.extract_worker and self.extract_worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Confirm Exit",
                "Extraction is still running. Are you sure you want to exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return

        if self._update_manager._worker and self._update_manager._worker.isRunning():
            self._update_manager._worker.quit()
            self._update_manager._worker.wait(CLOSE_WAIT_MS)

        if self.worker and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait(CLOSE_WAIT_MS)

        if self.extract_worker and self.extract_worker.isRunning():
            self.extract_worker._shutdown_requested = True
            self.extract_worker.quit()
            self.extract_worker.wait(5000)

        self._config.save_window_geometry(self.saveGeometry())
        self._config.save_window_state(self.saveState())
        event.accept()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _init_ui(self) -> None:
        self.setWindowTitle(f"{APP_NAME} v{VERSION}")
        self.setMinimumSize(750, 700)
        self.setWindowFlags(Qt.WindowType.Window)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        outer_layout = QVBoxLayout(central_widget)
        outer_layout.setSpacing(0)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        self._stack = QStackedWidget()
        outer_layout.addWidget(self._stack)

        # --- Page 0: Main extractor ---
        self._extractor_page = QWidget()
        main_layout = QVBoxLayout(self._extractor_page)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(10, 10, 10, 10)

        self._build_menubar()
        create_toolbar(self)

        # Input section
        input_group = _make_group("")
        input_layout = QVBoxLayout(input_group)
        input_layout.setSpacing(6)
        input_layout.setContentsMargins(10, 4, 10, 8)

        url_layout = QHBoxLayout()
        url_layout.setSpacing(8)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter FitGirl repack URL...")
        self.url_input.returnPressed.connect(self.start_fetch)

        self.paste_btn = QPushButton("Paste")
        self.paste_btn.clicked.connect(self.paste_from_clipboard)
        self.paste_btn.setFixedWidth(80)
        self.paste_btn.setFixedHeight(32)

        self.fetch_btn = QPushButton("Fetch")
        self.fetch_btn.clicked.connect(self.start_fetch)
        self.fetch_btn.setFixedWidth(80)
        self.fetch_btn.setFixedHeight(32)

        url_layout.addWidget(self.url_input)
        url_layout.addWidget(self.paste_btn)
        url_layout.addWidget(self.fetch_btn)
        input_layout.addLayout(url_layout)
        main_layout.addWidget(input_group)

        # Status label
        self.status_label = QLabel("● Ready")
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {ModernStyle.TEXT_SECONDARY};
                font-size: 11px;
                padding: 4px 8px;
                background-color: {ModernStyle.BG_SECONDARY};
                border-radius: 4px;
            }}
        """)
        main_layout.addWidget(self.status_label)

        # Splitter
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(2)

        # Parts section
        parts_widget = QWidget()
        parts_layout = QVBoxLayout(parts_widget)
        parts_layout.setContentsMargins(0, 0, 0, 0)
        parts_layout.setSpacing(4)

        parts_header = QHBoxLayout()
        parts_label = QLabel("Parts")
        parts_label.setStyleSheet(ModernStyle.header_label_style())
        self.parts_count = QLabel("0 found")
        self.parts_count.setStyleSheet(ModernStyle.muted_label_style())
        parts_header.addWidget(parts_label)
        parts_header.addStretch()
        parts_header.addWidget(self.parts_count)
        parts_layout.addLayout(parts_header)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(150)
        scroll_area.setStyleSheet(
            "QScrollArea { border: none; background-color: transparent; }"
        )

        self.scroll_widget = QWidget()
        self.scroll_widget.setStyleSheet(
            f"background-color: {ModernStyle.BG_PRIMARY};"
        )
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_layout.setSpacing(2)
        self.scroll_layout.setContentsMargins(2, 2, 2, 2)
        scroll_area.setWidget(self.scroll_widget)
        parts_layout.addWidget(scroll_area)

        # Parts control buttons
        control_layout = QHBoxLayout()
        control_layout.setSpacing(6)

        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self.select_all)
        self.select_all_btn.setFixedHeight(28)

        self.deselect_all_btn = QPushButton("Deselect All")
        self.deselect_all_btn.clicked.connect(self.deselect_all)
        self.deselect_all_btn.setFixedHeight(28)

        self.custom_select_btn = QPushButton("Custom Select Files")
        self.custom_select_btn.clicked.connect(self.open_file_selection)
        self.custom_select_btn.setFixedHeight(28)
        self.custom_select_btn.setEnabled(False)

        control_layout.addWidget(self.select_all_btn)
        control_layout.addWidget(self.deselect_all_btn)
        control_layout.addWidget(self.custom_select_btn)
        control_layout.addStretch()

        # Browser combo
        self.browser_combo = QComboBox()
        self.browser_combo.setFixedHeight(32)
        self.browser_combo.setFixedWidth(140)
        self.browser_combo.setStyleSheet(ModernStyle.combobox_style())
        self.browser_combo.setToolTip(
            "Select which Chromium-based browser to use for V2 extraction.\n"
            "Auto Detect will use the first available browser found."
        )

        detected = BrowserDetector.find_all_browsers()
        self.browser_combo.addItem("Auto Detect", None)
        self._browser_paths: dict[str, str | None] = {"Auto Detect": None}
        for name in ["Chrome", "Edge", "Brave", "Chromium"]:
            if name in detected:
                self.browser_combo.addItem(name, name)
                self._browser_paths[name] = detected[name]

        if self._selected_browser and self._selected_browser in detected:
            for i in range(self.browser_combo.count()):
                if self.browser_combo.itemData(i) == self._selected_browser:
                    self.browser_combo.setCurrentIndex(i)
                    break

        self.browser_combo.currentIndexChanged.connect(self._on_browser_changed)
        control_layout.addWidget(self.browser_combo)

        self.extract_v1_btn = QPushButton("Extract V1")
        self.extract_v1_btn.clicked.connect(lambda: self.start_extraction(method="v1"))
        self.extract_v1_btn.setEnabled(False)
        self.extract_v1_btn.setFixedHeight(32)
        self.extract_v1_btn.setFixedWidth(110)
        self.extract_v1_btn.setStyleSheet(
            self.extract_v1_btn.styleSheet()
            + "QPushButton { padding-left: 14px; padding-right: 14px; }"
        )

        self.extract_v2_btn = QPushButton("Extract V2")
        self.extract_v2_btn.clicked.connect(lambda: self.start_extraction(method="v2"))
        self.extract_v2_btn.setEnabled(False)
        self.extract_v2_btn.setFixedHeight(32)
        self.extract_v2_btn.setFixedWidth(110)
        self.extract_v2_btn.setStyleSheet(
            self.extract_v2_btn.styleSheet()
            + "QPushButton { padding-left: 14px; padding-right: 14px; }"
        )

        control_layout.addWidget(self.extract_v1_btn)
        control_layout.addWidget(self.extract_v2_btn)
        parts_layout.addLayout(control_layout)

        splitter.addWidget(parts_widget)

        # Output section
        output_widget = QWidget()
        output_layout = QVBoxLayout(output_widget)
        output_layout.setContentsMargins(0, 0, 0, 0)
        output_layout.setSpacing(4)

        output_header = QHBoxLayout()
        output_label = QLabel("Links")
        output_label.setStyleSheet(ModernStyle.header_label_style())
        self.link_count = QLabel("0 extracted")
        self.link_count.setStyleSheet(ModernStyle.muted_label_style())
        output_header.addWidget(output_label)
        output_header.addStretch()
        output_header.addWidget(self.link_count)
        output_layout.addLayout(output_header)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("SF Mono", 11))
        output_layout.addWidget(self.output_text)

        output_control = QHBoxLayout()
        output_control.setSpacing(6)

        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_links)
        self.save_btn.setFixedHeight(28)

        self.copy_btn = QPushButton("Copy")
        self.copy_btn.clicked.connect(self.copy_output)
        self.copy_btn.setFixedHeight(28)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_output)
        self.clear_btn.setFixedHeight(28)

        output_control.addStretch()
        output_control.addWidget(self.save_btn)
        output_control.addWidget(self.copy_btn)
        output_control.addWidget(self.clear_btn)
        output_layout.addLayout(output_control)

        splitter.addWidget(output_widget)
        splitter.setSizes([300, 350])
        main_layout.addWidget(splitter)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(20)
        main_layout.addWidget(self.progress_bar)

        self.statusBar().showMessage("Ready")

        # --- Page 1: Explorer ---
        self._explorer_widget = FitGirlExplorerWidget()
        self._explorer_widget.send_to_extractor.connect(self._send_url_to_extractor)
        self._stack.addWidget(self._extractor_page)
        self._stack.addWidget(self._explorer_widget)
        self._stack.setCurrentIndex(0)

    # ------------------------------------------------------------------
    # Menubar
    # ------------------------------------------------------------------

    def _build_menubar(self) -> None:
        menubar = self.menuBar()

        # File / Menu
        file_menu = menubar.addMenu("Menu")

        explorer_action = QAction("FitGirl Explorer", self)
        explorer_action.triggered.connect(lambda: self._switch_page(1))
        file_menu.addAction(explorer_action)

        extractor_action = QAction("Extractor", self)
        extractor_action.triggered.connect(lambda: self._switch_page(0))
        file_menu.addAction(extractor_action)

        file_menu.addSeparator()

        extract_v1_action = QAction("Extract V1 (Cloudflare)", self)
        extract_v1_action.triggered.connect(lambda: self.start_extraction(method="v1"))
        file_menu.addAction(extract_v1_action)

        extract_v2_action = QAction("Extract V2 (Browser)", self)
        extract_v2_action.triggered.connect(lambda: self.start_extraction(method="v2"))
        file_menu.addAction(extract_v2_action)

        file_menu.addSeparator()

        save_action = QAction("Save Links...", self)
        save_action.triggered.connect(self.save_links)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu("Edit")

        select_all_action = QAction("Select All", self)
        select_all_action.triggered.connect(self.select_all)
        edit_menu.addAction(select_all_action)

        deselect_all_action = QAction("Deselect All", self)
        deselect_all_action.triggered.connect(self.deselect_all)
        edit_menu.addAction(deselect_all_action)

        edit_menu.addSeparator()

        copy_action = QAction("Copy Links", self)
        copy_action.triggered.connect(self.copy_output)
        edit_menu.addAction(copy_action)

        clear_action = QAction("Clear Output", self)
        clear_action.triggered.connect(self.clear_output)
        edit_menu.addAction(clear_action)

        # Settings menu
        settings_menu = menubar.addMenu("Settings")

        delays_action = QAction("Delays", self)
        delays_action.triggered.connect(self.open_settings)
        settings_menu.addAction(delays_action)

        browser_action = QAction("Browser", self)
        browser_action.triggered.connect(self.open_browser_settings)
        settings_menu.addAction(browser_action)

        settings_menu.addSeparator()

        check_update_action = QAction("Check for Updates", self)
        check_update_action.triggered.connect(self.check_for_updates)
        settings_menu.addAction(check_update_action)

        self._uninstaller_path = os.path.join(
            os.path.dirname(os.path.abspath(sys.argv[0])), "unins000.exe"
        )
        if os.path.isfile(self._uninstaller_path):
            uninstall_action = QAction("Uninstall FitFetch", self)
            uninstall_action.triggered.connect(self._run_uninstaller)
            settings_menu.addAction(uninstall_action)

        # Help menu
        help_menu = menubar.addMenu("Help")

        how_to_use_action = QAction("How to Use", self)
        how_to_use_action.triggered.connect(self.show_help)
        help_menu.addAction(how_to_use_action)

        about_action = QAction("About FitFetch", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    # ------------------------------------------------------------------
    # Page switching
    # ------------------------------------------------------------------

    def _switch_page(self, index: int) -> None:
        self._stack.setCurrentIndex(index)

    def _send_url_to_extractor(self, url: str) -> None:
        self.url_input.setText(url)
        self._switch_page(0)
        self.statusBar().showMessage("URL loaded — fetching links...", 3000)
        self.start_fetch()

    # ------------------------------------------------------------------
    # Clipboard / validation
    # ------------------------------------------------------------------

    def paste_from_clipboard(self) -> None:
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        if not text:
            self.statusBar().showMessage("Clipboard is empty", 3000)
            return
        if self._is_valid_fitgirl_url(text):
            self.url_input.setText(text)
            self.statusBar().showMessage("Valid FitGirl URL pasted from clipboard", 3000)
            self.start_fetch()
        else:
            self.statusBar().showMessage(
                "Invalid URL! Please enter a valid FitGirl repack URL", 5000
            )
            QMessageBox.warning(
                self,
                "Invalid URL",
                "The pasted URL is not a valid FitGirl repack URL.\n\n"
                "Expected format: https://fitgirl-repacks.site/xxx\n\n"
                "Example: https://fitgirl-repacks.site/grand-theft-auto-v/",
            )

    def _is_valid_fitgirl_url(self, url: str) -> bool:
        return bool(url and RE_FITGIRL_URL.match(url))

    # ------------------------------------------------------------------
    # Dialogs
    # ------------------------------------------------------------------

    def show_about(self) -> None:
        AboutDialog(self).exec()

    def show_help(self) -> None:
        HelpDialog(self).exec()

    def open_settings(self) -> None:
        dialog = SettingsDialog(self._config.v1_delay, self._config.v2_delay, self)
        if dialog.exec():
            self._config.v1_delay = dialog.get_v1_delay()
            self._config.v2_delay = dialog.get_v2_delay()
            self.statusBar().showMessage(
                f"Settings updated: V1 delay={dialog.get_v1_delay()}ms, "
                f"V2 delay={dialog.get_v2_delay() / 1000}s",
                3000,
            )

    def open_browser_settings(self) -> None:
        detected = BrowserDetector.find_all_browsers()
        selected = self._selected_browser
        if selected:
            active_path = BrowserDetector.get_browser_path(selected)
        else:
            active_path = BrowserDetector.detect_default_browser()
        BrowserSettingsDialog(detected, selected, active_path, self).exec()

    def open_file_selection(self) -> None:
        """Open the advanced file selection dialog and apply the chosen
        selection back to the parts checkboxes."""
        if not self.links:
            return
        dialog = FileSelectionDialog(
            self.links,
            initial_state=getattr(self, "_file_select_state", None),
            parent=self,
        )
        if dialog.exec():
            selected_urls = set(dialog.get_selected_links())
            for checkbox, link in self.checkbox_links.items():
                checkbox.setChecked(link in selected_urls)
            self.update_parts_count()
            # persist selection for next open
            self._file_select_state = dialog.get_selection_state()

    def check_for_updates(self) -> None:
        self.statusBar().showMessage("Checking for updates...", 5000)
        self._update_manager.check_for_updates(silent=False)

    def _run_uninstaller(self) -> None:
        reply = QMessageBox.question(
            self,
            "Uninstall FitFetch",
            "Are you sure you want to uninstall FitFetch?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            import subprocess

            subprocess.Popen([self._uninstaller_path, "/VERYSILENT"])
            self.close()

    # ------------------------------------------------------------------
    # Update callbacks
    # ------------------------------------------------------------------

    def _on_update_found(
        self, tag: str, body: str, html_url: str, published_at: str, download_url: str
    ) -> None:
        VersionDialog(
            title=f"Update Available: v{tag}",
            subtitle=f"Current version: <b>{VERSION}</b> &rarr; New version: <b>{tag}</b>",
            body=body,
            html_url=html_url,
            published_at=published_at,
            extra_buttons=[
                (
                    "Download",
                    lambda: QDesktopServices.openUrl(
                        QUrl(download_url if download_url else html_url)
                    ),
                )
            ],
            parent=self,
        ).exec()

    def _on_update_error(self, message: str) -> None:
        QMessageBox.warning(self, "Update Check Failed", message)

    def _on_no_update(
        self, tag: str, body: str, html_url: str, published_at: str
    ) -> None:
        VersionDialog(
            title=f"Up to Date: v{VERSION}",
            subtitle=f"Current version: <b>{VERSION}</b> &rarr; Latest: <b>{tag}</b>",
            body=body,
            html_url=html_url,
            published_at=published_at,
            extra_buttons=[],
            parent=self,
        ).exec()

    # ------------------------------------------------------------------
    # Status / count helpers
    # ------------------------------------------------------------------

    def update_status(self, message: str) -> None:
        self.status_label.setText(f"● {message}")
        self.statusBar().showMessage(message)

    def update_parts_count(self) -> None:
        total = len(self.checkbox_links)
        selected = len(self.get_selected_links())
        self.parts_count.setText(f"{selected}/{total} selected")

    def update_link_count(self) -> None:
        text = self.output_text.toPlainText().strip()
        if text:
            count = len(text.splitlines())
            self.link_count.setText(f"{count} links")
        else:
            self.link_count.setText("0 extracted")

    def add_output(self, text: str) -> None:
        self.output_text.append(text)
        cursor = self.output_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.output_text.setTextCursor(cursor)
        self.update_link_count()

    # ------------------------------------------------------------------
    # Checkbox management
    # ------------------------------------------------------------------

    def clear_checkboxes(self) -> None:
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.checkboxes.clear()
        self.checkbox_links.clear()
        self.checkbox_widgets.clear()
        self.custom_select_btn.setEnabled(False)
        self.parts_count.setText("0 found")

    def populate_checkboxes(self, links: list[str]) -> None:
        self.clear_checkboxes()
        self.links = links

        if not links:
            self.update_status("No links found")
            return

        def _sort_key(url: str) -> int:
            try:
                m = RE_PART_NUM.search(extract_filename(url))
                return int(m.group(1)) if m else 0
            except (ValueError, TypeError):
                return 0

        sorted_links = sorted(links, key=_sort_key)

        for link in sorted_links:
            filename = extract_filename(link)
            part_num = extract_part_num(filename)

            container = QWidget()
            container.setStyleSheet(f"""
                QWidget {{
                    background-color: {ModernStyle.BG_SECONDARY};
                    border-radius: 4px;
                    padding: 2px;
                }}
                QWidget:hover {{
                    background-color: {ModernStyle.BG_TERTIARY};
                }}
            """)
            container_layout = QHBoxLayout(container)
            container_layout.setContentsMargins(6, 3, 6, 3)
            container_layout.setSpacing(6)

            checkbox = ClickableCheckBox("")
            checkbox.stateChanged.connect(
                lambda state, ref=link: self.on_checkbox_changed(ref, state)
            )
            self.checkbox_links[checkbox] = link

            part_label = QLabel(f"#{part_num}")
            part_label.setFixedWidth(40)
            part_label.setStyleSheet(f"""
                QLabel {{
                    color: {ModernStyle.ACCENT};
                    font-weight: 600;
                    font-size: 11px;
                    background-color: {ModernStyle.BG_TERTIARY};
                    border-radius: 3px;
                    padding: 1px 4px;
                }}
            """)

            name_label = QLabel(filename)
            name_label.setStyleSheet(f"""
                QLabel {{
                    color: {ModernStyle.TEXT_PRIMARY};
                    font-size: 11px;
                    padding: 1px 0px;
                }}
            """)
            name_label.setCursor(Qt.CursorShape.PointingHandCursor)
            name_label.mousePressEvent = lambda _, cb=checkbox: cb.toggle()

            container_layout.addWidget(checkbox)
            container_layout.addWidget(part_label)
            container_layout.addWidget(name_label)
            container_layout.addStretch()

            self.scroll_layout.addWidget(container)
            self.checkboxes.append(checkbox)
            self.checkbox_widgets.append(container)

            checkbox.setChecked(True)

        status = f"Found {len(links)} parts"
        elapsed = time.time() - self._fetch_start_time
        status += f" ({elapsed:.1f}s)"
        if self._fetched_size:
            status += f" ({self._fetched_size})"
        self.update_status(status)
        self.parts_count.setText(f"{len(links)} found")
        self.extract_v1_btn.setEnabled(True)
        self.extract_v2_btn.setEnabled(True)
        self.custom_select_btn.setEnabled(True)

    def on_checkbox_changed(self, link: str, state: int) -> None:
        self.update_parts_count()

    def _on_browser_changed(self, index: int) -> None:
        self._selected_browser = self.browser_combo.currentData()
        self._config.selected_browser = self._selected_browser

    def select_all(self) -> None:
        for checkbox in self.checkboxes:
            checkbox.setChecked(True)
        self.update_parts_count()

    def deselect_all(self) -> None:
        for checkbox in self.checkboxes:
            checkbox.setChecked(False)
        self.update_parts_count()

    def get_selected_links(self) -> list[str]:
        return [
            link
            for checkbox, link in self.checkbox_links.items()
            if checkbox.isChecked()
        ]

    # ------------------------------------------------------------------
    # Fetch
    # ------------------------------------------------------------------

    def start_fetch(self) -> None:
        if self.worker and self.worker.isRunning():
            return

        url = self.url_input.text().strip()
        if not url:
            QMessageBox.critical(self, "Error", "Please enter a valid URL")
            return

        # If input doesn't look like a URL, search in the explorer instead
        if not url.lower().startswith(("http://", "https://")):
            self._explorer_widget.search_input.setText(url)
            self._switch_page(1)
            self._explorer_widget._on_search()
            self.statusBar().showMessage(
                f"Searching FitGirl for \"{url}\"...", 3000
            )
            return

        self.fetch_btn.setEnabled(False)
        self.extract_v1_btn.setEnabled(False)
        self.extract_v2_btn.setEnabled(False)
        self.clear_checkboxes()
        self.output_text.clear()
        self.progress_bar.setValue(0)
        self.link_count.setText("0 extracted")
        self._fetch_start_time = time.time()

        from ..workers.fitgirl_fetch_worker import FitGirlFetchWorker

        self.worker = FitGirlFetchWorker(url, parent=self)
        self.worker.status_update.connect(self.update_status)
        self.worker.fetch_complete.connect(self.on_fetch_complete)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.size_info.connect(self._on_size_info)
        self.worker.start()

    def _on_size_info(self, size_text: str) -> None:
        self._fetched_size = size_text

    def on_fetch_complete(self, links: list[str]) -> None:
        self.populate_checkboxes(links)
        self.fetch_btn.setEnabled(True)

    def on_error(self, error_msg: str) -> None:
        self.update_status(f"Error: {error_msg}")
        self.fetch_btn.setEnabled(True)
        QMessageBox.critical(self, "Error", f"An error occurred:\n{error_msg}")

    # ------------------------------------------------------------------
    # Extraction
    # ------------------------------------------------------------------

    def start_extraction(self, method: str = "v1") -> None:
        if self.extract_worker and self.extract_worker.isRunning():
            return

        selected = self.get_selected_links()
        if not selected:
            QMessageBox.warning(self, "Warning", "No items selected")
            return

        self.output_text.clear()
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(len(selected))
        self.link_count.setText("0 extracted")

        self.fetch_btn.setEnabled(False)
        self.extract_v1_btn.setEnabled(False)
        self.extract_v2_btn.setEnabled(False)
        self._extract_start_time = time.time()

        if method == "v1":
            self.extract_worker = CloudflareWorker(
                selected,
                threads=MAX_CF_THREADS,
                delay=self._config.v1_delay,
                parent=self,
            )
            self.update_status("Starting V1 extraction (Cloudflare bypass)...")
        else:
            browser_path = self._browser_manager.get_browser_path()
            if not browser_path:
                QMessageBox.critical(
                    self,
                    "No Browser Found",
                    "No Chromium-based browser found on your system.\n\n"
                    "Please install one of the following browsers:\n"
                    "- Google Chrome\n"
                    "- Microsoft Edge\n"
                    "- Brave Browser\n"
                    "- Chromium\n\n"
                    "Then restart the application and try again.",
                )
                self.fetch_btn.setEnabled(True)
                self.extract_v1_btn.setEnabled(True)
                self.extract_v2_btn.setEnabled(True)
                return

            self.extract_worker = ZendriverWorker(
                selected,
                delay=self._config.v2_delay,
                browser_executable_path=browser_path,
                parent=self,
            )
            self.update_status(
                f"Starting V2 extraction (Browser: {os.path.basename(browser_path)})..."
            )

        self.extract_worker.status_update.connect(self.update_status)
        self.extract_worker.progress_update.connect(self.progress_bar.setValue)
        self.extract_worker.link_found.connect(self.add_output)
        self.extract_worker.error_occurred.connect(self.on_extract_error)
        self.extract_worker.extraction_complete.connect(self.on_extraction_complete)
        self.extract_worker.start()

    def on_extract_error(self, error_msg: str) -> None:
        self.update_status(f"Error: {error_msg}")
        self.fetch_btn.setEnabled(True)
        self.extract_v1_btn.setEnabled(True)
        self.extract_v2_btn.setEnabled(True)
        QMessageBox.critical(self, "Error", f"Extraction error:\n{error_msg}")

    def on_extraction_complete(self) -> None:
        self.fetch_btn.setEnabled(True)
        self.extract_v1_btn.setEnabled(True)
        self.extract_v2_btn.setEnabled(True)
        self.update_link_count()
        count = self.link_count.text()
        elapsed = time.time() - self._extract_start_time
        self.update_status(f"Extraction complete ({count}) ({elapsed:.1f}s)")

    # ------------------------------------------------------------------
    # Save / Copy / Clear
    # ------------------------------------------------------------------

    def save_links(self) -> None:
        text = self.output_text.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Info", "No links to save")
            return

        default_name = f"fitgirl_links_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Links", default_name, "Text Files (*.txt);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(text)
                self.update_status(
                    f"Saved {len(text.splitlines())} links to {os.path.basename(file_path)}"
                )
                self.current_file = file_path
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file:\n{str(e)}")

    def copy_output(self) -> None:
        text = self.output_text.toPlainText()
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            count = len(text.splitlines())
            self.update_status(f"Copied {count} links to clipboard")
            self.statusBar().showMessage(f"Copied {count} links", 2000)
        else:
            QMessageBox.information(self, "Info", "Nothing to copy")

    def clear_output(self) -> None:
        self.output_text.clear()
        self.progress_bar.setValue(0)
        self.link_count.setText("0 extracted")
        self.update_status("Cleared output")

    # ------------------------------------------------------------------
    # Startup / show
    # ------------------------------------------------------------------

    def showEvent(self, event) -> None:
        super().showEvent(event)
        QTimer.singleShot(STARTUP_UPDATE_DELAY_MS, self._startup_update_check)

    def _startup_update_check(self) -> None:
        if self._startup_update_shown:
            return
        self._startup_update_shown = True
        self._update_manager.check_for_updates(silent=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_group(title: str) -> QWidget:
    """Create a styled QGroupBox (inlined to avoid circular import)."""
    from PyQt6.QtWidgets import QGroupBox

    group = QGroupBox(title)
    group.setStyleSheet(f"""
        QGroupBox {{
            font-weight: 600;
            border: 1px solid {ModernStyle.BORDER};
            border-radius: {ModernStyle.RADIUS}px;
            margin-top: 8px;
            padding-top: 8px;
            background-color: {ModernStyle.BG_SECONDARY};
            font-size: {ModernStyle.FONT_SMALL}px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 6px 0 6px;
            color: {ModernStyle.TEXT_SECONDARY};
        }}
    """)
    return group
