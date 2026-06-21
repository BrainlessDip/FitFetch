import sys
import re
import time
import os
import asyncio
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import nodriver as uc
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QCheckBox,
    QTextEdit,
    QProgressBar,
    QScrollArea,
    QGroupBox,
    QMessageBox,
    QStyleFactory,
    QSplitter,
    QFileDialog,
    QToolBar,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QAction, QIcon
import traceback

# Version
VERSION = "1.0.0"
APP_NAME = "FitFetch"


class AsyncWorker(QThread):
    """Base class for async operations"""

    status_update = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.loop = None

    def run(self):
        """Run the async task"""
        try:
            # Create new event loop for this thread
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

            # Run the async method
            self.loop.run_until_complete(self.async_run())

        except Exception as e:
            self.error_occurred.emit(
                f"Thread error: {str(e)}\n{traceback.format_exc()}"
            )
        finally:
            if self.loop:
                self.loop.close()

    async def async_run(self):
        """Override this method with async logic"""
        raise NotImplementedError


class FetchWorker(AsyncWorker):
    fetch_complete = pyqtSignal(list)

    def __init__(self, url):
        super().__init__()
        self.url = url

    async def async_run(self):
        try:
            self.status_update.emit("Fetching links...")

            html = requests.get(
                self.url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
                timeout=30,
            ).text

            soup = BeautifulSoup(html, "html.parser")

            links = list(
                {
                    a["href"]
                    for a in soup.find_all("a", href=True)
                    if "fuckingfast.co" in a["href"]
                }
            )

            self.fetch_complete.emit(links)

        except Exception as e:
            self.error_occurred.emit(f"Fetch error: {str(e)}\n{traceback.format_exc()}")


class ExtractWorker(AsyncWorker):
    progress_update = pyqtSignal(int)
    link_found = pyqtSignal(str)
    extraction_complete = pyqtSignal()

    def __init__(self, links):
        super().__init__()
        self.links = links
        self.browser = None

    async def async_run(self):
        try:
            self.status_update.emit("Initializing browser...")

            # Start browser with nodriver
            self.status_update.emit("Starting Chrome browser...")
            self.browser = await uc.start(
                headless=False,
                window_size=(1200, 800),
                no_sandbox=True,
                disable_gpu=True,
            )

            self.status_update.emit(f"Processing {len(self.links)} links...")

            for i, link in enumerate(self.links, 1):
                filename = link.split("/")[-1]
                self.status_update.emit(
                    f"[{i}/{len(self.links)}] Processing {filename}"
                )

                try:
                    self.status_update.emit(f"Loading {filename}...")

                    # Navigate to the link - get returns a Tab object
                    tab = await self.browser.get(link)
                    await tab.sleep(3)  # Wait for page to load using nodriver's sleep

                    self.status_update.emit(f"Extracting from {filename}...")

                    # Get page source using get_content() method
                    page_source = await tab.get_content()

                    # Try multiple patterns
                    patterns = [
                        r'window\.open\("([^"]+)"\)',
                        r"window\.open\(\'([^\']+)\'\)",
                        r'href="([^"]*fuckingfast[^"]*)"',
                        r"href='([^']*fuckingfast[^']*)'",
                        r'https?://[^\s"\']*fuckingfast[^\s"\']*',
                    ]

                    match = None
                    for pattern in patterns:
                        match = re.search(pattern, page_source)
                        if match:
                            break

                    if match:
                        extracted_url = (
                            match.group(1)
                            if len(match.groups()) > 0
                            else match.group(0)
                        )
                        self.link_found.emit(extracted_url)
                        self.status_update.emit(f"Extracted: {filename}")
                    else:
                        # Try alternative: look for elements containing "fuckingfast"
                        try:
                            # Find all links with href containing "fuckingfast"
                            elements = await tab.find_all(text="fuckingfast", timeout=2)
                            found = False

                            if elements:
                                for elem in elements:
                                    # Try to get parent element (which might be the link)
                                    parent = await elem.parent()
                                    if parent:
                                        href = await parent.get_attribute("href")
                                        if href and "fuckingfast" in href:
                                            self.link_found.emit(href)
                                            self.status_update.emit(
                                                f"Extracted: {filename}"
                                            )
                                            found = True
                                            break

                            if not found:
                                # Try using select_all with css selector
                                links = await tab.select_all(
                                    "a[href*='fuckingfast']", timeout=2
                                )
                                if links:
                                    href = await links[0].get_attribute("href")
                                    if href:
                                        self.link_found.emit(href)
                                        self.status_update.emit(
                                            f"Extracted: {filename}"
                                        )
                                        found = True

                                if not found:
                                    self.link_found.emit(
                                        f"FAILED: {filename} - No direct link found"
                                    )
                                    self.status_update.emit(f"Failed: {filename}")
                        except Exception as e:
                            self.link_found.emit(
                                f"FAILED: {filename} - No direct link found"
                            )
                            self.status_update.emit(f"Failed: {filename}")

                except Exception as e:
                    error_msg = str(e)
                    self.link_found.emit(f"ERROR: {filename} - {error_msg}")
                    self.status_update.emit(f"Error: {filename} - {error_msg}")

                self.progress_update.emit(i)

            self.status_update.emit("Extraction complete")
            self.extraction_complete.emit()

        except Exception as e:
            error_msg = f"Browser error: {str(e)}\n{traceback.format_exc()}"
            self.error_occurred.emit(error_msg)
        finally:
            if self.browser:
                try:
                    self.status_update.emit("Closing browser...")
                    await self.browser.stop()
                except:
                    pass


class ClickableCheckBox(QCheckBox):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle()
            event.accept()
        else:
            super().mousePressEvent(event)


class ModernStyle:
    """Modern dark theme with compact design"""

    # Colors
    BG_PRIMARY = "#0d1117"
    BG_SECONDARY = "#161b22"
    BG_TERTIARY = "#21262d"
    BG_HOVER = "#30363d"
    BG_ACTIVE = "#3d444d"

    TEXT_PRIMARY = "#e6edf3"
    TEXT_SECONDARY = "#8b949e"
    TEXT_MUTED = "#484f58"

    BORDER = "#30363d"
    BORDER_ACTIVE = "#58a6ff"

    ACCENT = "#58a6ff"
    ACCENT_HOVER = "#79c0ff"
    ACCENT_PRESSED = "#1f6feb"

    SUCCESS = "#3fb950"
    WARNING = "#d29922"
    ERROR = "#f85149"

    # Sizes
    PADDING_SMALL = 4
    PADDING_MEDIUM = 8
    PADDING_LARGE = 12
    RADIUS = 6
    FONT_SIZE = 12
    FONT_SMALL = 11


class ModernGroupBox(QGroupBox):
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self.setStyleSheet(f"""
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


class FitFetchApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.checkboxes = []
        self.checkbox_links = {}
        self.checkbox_widgets = []
        self.links = []
        self.current_file = None
        self.worker = None
        self.extract_worker = None

        self.init_ui()
        self.apply_modern_style()

    def apply_modern_style(self):
        """Apply modern dark theme with compact design"""
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {ModernStyle.BG_PRIMARY};
            }}
            
            QWidget {{
                background-color: transparent;
                color: {ModernStyle.TEXT_PRIMARY};
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                font-size: {ModernStyle.FONT_SIZE}px;
            }}
            
            QPushButton {{
                background-color: {ModernStyle.BG_TERTIARY};
                border: 1px solid {ModernStyle.BORDER};
                border-radius: {ModernStyle.RADIUS}px;
                color: {ModernStyle.TEXT_PRIMARY};
                padding: 6px 14px;
                font-weight: 500;
                font-size: {ModernStyle.FONT_SMALL}px;
            }}
            QPushButton:hover {{
                background-color: {ModernStyle.BG_HOVER};
                border-color: {ModernStyle.BORDER_ACTIVE};
            }}
            QPushButton:pressed {{
                background-color: {ModernStyle.BG_ACTIVE};
            }}
            QPushButton:disabled {{
                opacity: 0.5;
            }}
            
            QPushButton[primary="true"] {{
                background-color: {ModernStyle.ACCENT};
                border: none;
                color: {ModernStyle.TEXT_PRIMARY};
            }}
            QPushButton[primary="true"]:hover {{
                background-color: {ModernStyle.ACCENT_HOVER};
            }}
            QPushButton[primary="true"]:pressed {{
                background-color: {ModernStyle.ACCENT_PRESSED};
            }}
            
            QLineEdit {{
                background-color: {ModernStyle.BG_TERTIARY};
                border: 1px solid {ModernStyle.BORDER};
                border-radius: {ModernStyle.RADIUS}px;
                padding: 6px 10px;
                color: {ModernStyle.TEXT_PRIMARY};
                selection-background-color: {ModernStyle.ACCENT};
                font-size: {ModernStyle.FONT_SMALL}px;
            }}
            QLineEdit:focus {{
                border-color: {ModernStyle.BORDER_ACTIVE};
            }}
            QLineEdit::placeholder {{
                color: {ModernStyle.TEXT_MUTED};
            }}
            
            QTextEdit {{
                background-color: {ModernStyle.BG_PRIMARY};
                border: 1px solid {ModernStyle.BORDER};
                border-radius: {ModernStyle.RADIUS}px;
                padding: 8px;
                color: {ModernStyle.TEXT_PRIMARY};
                selection-background-color: {ModernStyle.ACCENT};
                font-family: 'SF Mono', 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                line-height: 1.5;
            }}
            QTextEdit:focus {{
                border-color: {ModernStyle.BORDER_ACTIVE};
            }}
            
            QProgressBar {{
                border: none;
                border-radius: 3px;
                text-align: center;
                height: 20px;
                background-color: {ModernStyle.BG_TERTIARY};
                color: {ModernStyle.TEXT_SECONDARY};
                font-size: 11px;
                font-weight: 500;
            }}
            QProgressBar::chunk {{
                background-color: {ModernStyle.ACCENT};
                border-radius: 3px;
            }}
            
            QCheckBox {{
                spacing: 8px;
                color: {ModernStyle.TEXT_PRIMARY};
                font-size: {ModernStyle.FONT_SMALL}px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: 1.5px solid {ModernStyle.BORDER};
                background-color: {ModernStyle.BG_TERTIARY};
            }}
            QCheckBox::indicator:checked {{
                background-color: {ModernStyle.ACCENT};
                border-color: {ModernStyle.ACCENT};
            }}
            QCheckBox::indicator:hover {{
                border-color: {ModernStyle.BORDER_ACTIVE};
            }}
            
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            
            QScrollBar:vertical {{
                background-color: {ModernStyle.BG_SECONDARY};
                width: 8px;
                border-radius: 4px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {ModernStyle.BG_TERTIARY};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {ModernStyle.BG_HOVER};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
                height: 0px;
            }}
            
            QScrollBar:horizontal {{
                background-color: {ModernStyle.BG_SECONDARY};
                height: 8px;
                border-radius: 4px;
                margin: 0px;
            }}
            QScrollBar::handle:horizontal {{
                background-color: {ModernStyle.BG_TERTIARY};
                border-radius: 4px;
                min-width: 20px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background-color: {ModernStyle.BG_HOVER};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                border: none;
                background: none;
                width: 0px;
            }}
            
            QSplitter::handle {{
                background-color: {ModernStyle.BORDER};
                height: 2px;
            }}
            QSplitter::handle:hover {{
                background-color: {ModernStyle.BORDER_ACTIVE};
            }}
            
            QLabel {{
                color: {ModernStyle.TEXT_PRIMARY};
                font-size: {ModernStyle.FONT_SMALL}px;
            }}
            
            QMenuBar {{
                background-color: {ModernStyle.BG_SECONDARY};
                color: {ModernStyle.TEXT_SECONDARY};
                border-bottom: 1px solid {ModernStyle.BORDER};
                padding: 2px 0px;
            }}
            QMenuBar::item:selected {{
                background-color: {ModernStyle.BG_TERTIARY};
                color: {ModernStyle.TEXT_PRIMARY};
            }}
            
            QMenu {{
                background-color: {ModernStyle.BG_SECONDARY};
                color: {ModernStyle.TEXT_PRIMARY};
                border: 1px solid {ModernStyle.BORDER};
                border-radius: {ModernStyle.RADIUS}px;
                padding: 4px 0px;
            }}
            QMenu::item {{
                padding: 6px 30px 6px 20px;
            }}
            QMenu::item:selected {{
                background-color: {ModernStyle.BG_TERTIARY};
            }}
            
            QStatusBar {{
                background-color: {ModernStyle.BG_SECONDARY};
                color: {ModernStyle.TEXT_SECONDARY};
                border-top: 1px solid {ModernStyle.BORDER};
                padding: 2px 8px;
                font-size: 11px;
            }}
            
            QToolTip {{
                background-color: {ModernStyle.BG_SECONDARY};
                color: {ModernStyle.TEXT_PRIMARY};
                border: 1px solid {ModernStyle.BORDER};
                border-radius: {ModernStyle.RADIUS}px;
                padding: 4px 8px;
            }}
        """)

    def init_ui(self):
        self.setWindowTitle(f"{APP_NAME} v{VERSION}")
        self.setMinimumSize(750, 700)
        self.setWindowFlags(Qt.WindowType.Window)

        # Central widget with compact spacing
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Menu Bar
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        fetch_action = QAction("Fetch Links", self)
        fetch_action.setShortcut("Ctrl+Return")
        fetch_action.triggered.connect(self.start_fetch)
        file_menu.addAction(fetch_action)

        extract_action = QAction("Extract Links", self)
        extract_action.setShortcut("Ctrl+E")
        extract_action.triggered.connect(self.start_extraction)
        file_menu.addAction(extract_action)

        file_menu.addSeparator()

        save_action = QAction("Save Links...", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_links)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu("Edit")

        select_all_action = QAction("Select All", self)
        select_all_action.setShortcut("Ctrl+A")
        select_all_action.triggered.connect(self.select_all)
        edit_menu.addAction(select_all_action)

        deselect_all_action = QAction("Deselect All", self)
        deselect_all_action.setShortcut("Ctrl+D")
        deselect_all_action.triggered.connect(self.deselect_all)
        edit_menu.addAction(deselect_all_action)

        edit_menu.addSeparator()

        copy_action = QAction("Copy Links", self)
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(self.copy_output)
        edit_menu.addAction(copy_action)

        clear_action = QAction("Clear Output", self)
        clear_action.triggered.connect(self.clear_output)
        edit_menu.addAction(clear_action)

        # Help menu
        help_menu = menubar.addMenu("Help")

        about_action = QAction("About FitFetch", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        # Toolbar
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setStyleSheet(f"""
            QToolBar {{
                background-color: {ModernStyle.BG_SECONDARY};
                border: none;
                border-bottom: 1px solid {ModernStyle.BORDER};
                padding: 2px;
                spacing: 4px;
            }}
            QToolBar::separator {{
                width: 1px;
                background-color: {ModernStyle.BORDER};
                margin: 4px 8px;
            }}
        """)
        self.addToolBar(toolbar)

        # Toolbar actions
        fetch_btn = QAction("Fetch", self)
        fetch_btn.setShortcut("Ctrl+Return")
        fetch_btn.triggered.connect(self.start_fetch)
        toolbar.addAction(fetch_btn)

        extract_btn = QAction("Extract", self)
        extract_btn.setShortcut("Ctrl+E")
        extract_btn.triggered.connect(self.start_extraction)
        toolbar.addAction(extract_btn)

        toolbar.addSeparator()

        select_all_btn = QAction("Select All", self)
        select_all_btn.setShortcut("Ctrl+A")
        select_all_btn.triggered.connect(self.select_all)
        toolbar.addAction(select_all_btn)

        deselect_all_btn = QAction("Deselect All", self)
        deselect_all_btn.setShortcut("Ctrl+D")
        deselect_all_btn.triggered.connect(self.deselect_all)
        toolbar.addAction(deselect_all_btn)

        toolbar.addSeparator()

        save_btn = QAction("Save", self)
        save_btn.setShortcut("Ctrl+S")
        save_btn.triggered.connect(self.save_links)
        toolbar.addAction(save_btn)

        copy_btn = QAction("Copy", self)
        copy_btn.setShortcut("Ctrl+C")
        copy_btn.triggered.connect(self.copy_output)
        toolbar.addAction(copy_btn)

        clear_btn = QAction("Clear", self)
        clear_btn.triggered.connect(self.clear_output)
        toolbar.addAction(clear_btn)

        # Input section - Compact
        input_group = ModernGroupBox("")
        input_layout = QVBoxLayout(input_group)
        input_layout.setSpacing(6)
        input_layout.setContentsMargins(10, 4, 10, 8)

        url_layout = QHBoxLayout()
        url_layout.setSpacing(8)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter FitGirl repack URL...")
        self.url_input.setText("https://fitgirl-repacks.site/grand-theft-auto-v/")
        self.url_input.returnPressed.connect(self.start_fetch)

        self.fetch_btn = QPushButton("Fetch")
        self.fetch_btn.setProperty("primary", True)
        self.fetch_btn.clicked.connect(self.start_fetch)
        self.fetch_btn.setFixedWidth(80)
        self.fetch_btn.setFixedHeight(32)

        url_layout.addWidget(self.url_input)
        url_layout.addWidget(self.fetch_btn)

        input_layout.addLayout(url_layout)
        main_layout.addWidget(input_group)

        # Status bar
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

        # Splitter for parts and output
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(2)

        # Parts section
        parts_widget = QWidget()
        parts_layout = QVBoxLayout(parts_widget)
        parts_layout.setContentsMargins(0, 0, 0, 0)
        parts_layout.setSpacing(4)

        parts_header = QHBoxLayout()
        parts_label = QLabel("Parts")
        parts_label.setStyleSheet(
            f"font-weight: 600; color: {ModernStyle.TEXT_SECONDARY}; font-size: 11px;"
        )
        self.parts_count = QLabel("0 found")
        self.parts_count.setStyleSheet(
            f"color: {ModernStyle.TEXT_MUTED}; font-size: 11px;"
        )

        parts_header.addWidget(parts_label)
        parts_header.addStretch()
        parts_header.addWidget(self.parts_count)
        parts_layout.addLayout(parts_header)

        # Scrollable area for checkboxes
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(150)
        scroll_area.setStyleSheet(
            "QScrollArea { border: none; background-color: transparent; }"
        )

        self.scroll_widget = QWidget()
        self.scroll_widget.setStyleSheet(f"background-color: {ModernStyle.BG_PRIMARY};")
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_layout.setSpacing(2)
        self.scroll_layout.setContentsMargins(2, 2, 2, 2)
        scroll_area.setWidget(self.scroll_widget)

        parts_layout.addWidget(scroll_area)

        # Parts control buttons - Compact
        control_layout = QHBoxLayout()
        control_layout.setSpacing(6)

        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self.select_all)
        self.select_all_btn.setFixedHeight(28)

        self.deselect_all_btn = QPushButton("Deselect All")
        self.deselect_all_btn.clicked.connect(self.deselect_all)
        self.deselect_all_btn.setFixedHeight(28)

        control_layout.addWidget(self.select_all_btn)
        control_layout.addWidget(self.deselect_all_btn)
        control_layout.addStretch()

        self.extract_btn = QPushButton("Extract")
        self.extract_btn.setProperty("primary", True)
        self.extract_btn.clicked.connect(self.start_extraction)
        self.extract_btn.setEnabled(False)
        self.extract_btn.setFixedHeight(32)
        self.extract_btn.setFixedWidth(80)

        control_layout.addWidget(self.extract_btn)
        parts_layout.addLayout(control_layout)

        splitter.addWidget(parts_widget)

        # Output section
        output_widget = QWidget()
        output_layout = QVBoxLayout(output_widget)
        output_layout.setContentsMargins(0, 0, 0, 0)
        output_layout.setSpacing(4)

        output_header = QHBoxLayout()
        output_label = QLabel("Links")
        output_label.setStyleSheet(
            f"font-weight: 600; color: {ModernStyle.TEXT_SECONDARY}; font-size: 11px;"
        )
        self.link_count = QLabel("0 extracted")
        self.link_count.setStyleSheet(
            f"color: {ModernStyle.TEXT_MUTED}; font-size: 11px;"
        )

        output_header.addWidget(output_label)
        output_header.addStretch()
        output_header.addWidget(self.link_count)
        output_layout.addLayout(output_header)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("SF Mono", 11))
        output_layout.addWidget(self.output_text)

        # Output control buttons - Compact
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

        # Progress bar - Compact
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(20)
        main_layout.addWidget(self.progress_bar)

        # Status bar
        self.statusBar().showMessage("Ready")

    def show_about(self):
        about_text = f"""
            <h2>{APP_NAME} v{VERSION}</h2>

            <p>
              A modern desktop application for extracting direct download links
              from FitGirl Repack pages quickly and efficiently.
            </p>

            <h3>Features</h3>
            <ul>
              <li>Extract direct FuckingFast download links</li>
              <li>Modern dark-themed interface</li>
              <li>Select or deselect individual parts</li>
              <li>One-click clipboard copying</li>
              <li>Export links to a text file</li>
              <li>Fast and reliable extraction</li>
            </ul>

            <p>
              Built with <b>PyQt6</b> and <b>nodriver</b>.
            </p>

            <hr>

            <p>
              <b>Developer:</b> Dip Dey
            </p>

            <p>
              <a href="https://github.com/BrainlessDip">
                GitHub
              </a>
              &nbsp;|&nbsp;
              <a href="https://www.facebook.com/brainless.dip">
                Facebook
              </a>
            </p>

            <p style="color: white;">
              Thank you for using {APP_NAME} ❤️
            </p>
            """
        msgBox = QMessageBox(self)
        msgBox.setWindowTitle(f"About {APP_NAME}")
        msgBox.setTextFormat(Qt.TextFormat.RichText)
        msgBox.setText(about_text)
        msgBox.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        msgBox.exec()

    def update_status(self, message):
        self.status_label.setText(f"● {message}")
        self.statusBar().showMessage(message)

    def update_parts_count(self):
        total = len(self.checkbox_links)
        selected = len(self.get_selected_links())
        self.parts_count.setText(f"{selected}/{total} selected")

    def update_link_count(self):
        text = self.output_text.toPlainText().strip()
        if text:
            count = len(text.splitlines())
            self.link_count.setText(f"{count} links")
        else:
            self.link_count.setText("0 extracted")

    def add_output(self, text):
        self.output_text.append(text)
        cursor = self.output_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.output_text.setTextCursor(cursor)
        self.update_link_count()

    def clear_checkboxes(self):
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.checkboxes.clear()
        self.checkbox_links.clear()
        self.checkbox_widgets.clear()
        self.parts_count.setText("0 found")

    def populate_checkboxes(self, links):
        self.clear_checkboxes()
        self.links = links

        if not links:
            self.update_status("No links found")
            return

        # Sort links naturally by part number
        def extract_number(url):
            try:
                filename = url.split("/")[-1]
                match = re.search(r"part(\d+)", filename, re.IGNORECASE)
                if match:
                    return int(match.group(1))
                return 0
            except:
                return 0

        sorted_links = sorted(links, key=extract_number)

        for idx, link in enumerate(sorted_links, 1):
            filename = link.split("/")[-1]
            part_match = re.search(r"part(\d+)", filename, re.IGNORECASE)
            part_num = part_match.group(1) if part_match else str(idx)

            # Container for compact display
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

            # Checkbox with click support
            checkbox = ClickableCheckBox("")
            checkbox.stateChanged.connect(
                lambda state, l=link: self.on_checkbox_changed(l, state)
            )
            self.checkbox_links[checkbox] = link

            # Part number badge
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

            # Filename - click to toggle checkbox
            name_label = QLabel(filename)
            name_label.setStyleSheet(f"""
                QLabel {{
                    color: {ModernStyle.TEXT_PRIMARY};
                    font-size: 11px;
                    padding: 1px 0px;
                }}
            """)
            name_label.setCursor(Qt.CursorShape.PointingHandCursor)

            def toggle_checkbox(event, cb=checkbox):
                cb.toggle()

            name_label.mousePressEvent = toggle_checkbox

            container_layout.addWidget(checkbox)
            container_layout.addWidget(part_label)
            container_layout.addWidget(name_label)
            container_layout.addStretch()

            self.scroll_layout.addWidget(container)
            self.checkboxes.append(checkbox)
            self.checkbox_widgets.append(container)

            checkbox.setChecked(True)

        self.update_status(f"Found {len(links)} parts")
        self.parts_count.setText(f"{len(links)} found")
        self.extract_btn.setEnabled(True)

    def on_checkbox_changed(self, link, state):
        self.update_parts_count()

    def select_all(self):
        for checkbox in self.checkboxes:
            checkbox.setChecked(True)
        self.update_parts_count()

    def deselect_all(self):
        for checkbox in self.checkboxes:
            checkbox.setChecked(False)
        self.update_parts_count()

    def get_selected_links(self):
        return [
            link
            for checkbox, link in self.checkbox_links.items()
            if checkbox.isChecked()
        ]

    def start_fetch(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.critical(self, "Error", "Please enter a valid URL")
            return

        self.fetch_btn.setEnabled(False)
        self.extract_btn.setEnabled(False)
        self.clear_checkboxes()
        self.output_text.clear()
        self.progress_bar.setValue(0)
        self.link_count.setText("0 extracted")

        self.worker = FetchWorker(url)
        self.worker.status_update.connect(self.update_status)
        self.worker.fetch_complete.connect(self.on_fetch_complete)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.start()

    def on_fetch_complete(self, links):
        self.populate_checkboxes(links)
        self.fetch_btn.setEnabled(True)

    def on_error(self, error_msg):
        self.update_status(f"Error: {error_msg}")
        self.fetch_btn.setEnabled(True)
        QMessageBox.critical(self, "Error", f"An error occurred:\n{error_msg}")

    def start_extraction(self):
        selected = self.get_selected_links()
        if not selected:
            QMessageBox.warning(self, "Warning", "No items selected")
            return

        self.output_text.clear()
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(len(selected))
        self.link_count.setText("0 extracted")

        self.fetch_btn.setEnabled(False)
        self.extract_btn.setEnabled(False)

        self.extract_worker = ExtractWorker(selected)
        self.extract_worker.status_update.connect(self.update_status)
        self.extract_worker.progress_update.connect(self.progress_bar.setValue)
        self.extract_worker.link_found.connect(self.add_output)
        self.extract_worker.error_occurred.connect(self.on_extract_error)
        self.extract_worker.extraction_complete.connect(self.on_extraction_complete)
        self.extract_worker.start()

    def on_extract_error(self, error_msg):
        self.update_status(f"Error: {error_msg}")
        self.fetch_btn.setEnabled(True)
        self.extract_btn.setEnabled(True)
        QMessageBox.critical(self, "Error", f"Extraction error:\n{error_msg}")

    def on_extraction_complete(self):
        self.fetch_btn.setEnabled(True)
        self.extract_btn.setEnabled(True)
        self.update_status("Extraction complete")
        self.update_link_count()

    def save_links(self):
        text = self.output_text.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Info", "No links to save")
            return

        # Generate default filename
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

    def copy_output(self):
        text = self.output_text.toPlainText()
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            count = len(text.splitlines())
            self.update_status(f"Copied {count} links to clipboard")
            self.statusBar().showMessage(f"Copied {count} links", 2000)
        else:
            QMessageBox.information(self, "Info", "Nothing to copy")

    def clear_output(self):
        self.output_text.clear()
        self.progress_bar.setValue(0)
        self.link_count.setText("0 extracted")
        self.update_status("Cleared output")

    def closeEvent(self, event):
        if (
            hasattr(self, "extract_worker")
            and self.extract_worker
            and self.extract_worker.isRunning()
        ):
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

        if hasattr(self, "worker") and self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        if (
            hasattr(self, "extract_worker")
            and self.extract_worker
            and self.extract_worker.isRunning()
        ):
            self.extract_worker.terminate()
            self.extract_worker.wait()

        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setWindowIcon(QIcon("favicon.ico"))
    app.setStyle(QStyleFactory.create("Fusion"))

    window = FitFetchApp()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
