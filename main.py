#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
FitFetch - FitGirl Repack Link Extractor
A modern GUI tool for extracting direct download links from FitGirl repack pages.
"""

import sys
import re
import os
import asyncio
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import cloudscraper
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import requests
from bs4 import BeautifulSoup
import zendriver as zd

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
    QDialog,
    QSpinBox,
    QFormLayout,
    QDialogButtonBox,
)
from PyQt6.QtCore import Qt, QThread, QObject, pyqtSignal, QUrl, QTimer
from PyQt6.QtGui import QFont, QAction, QIcon, QDesktopServices
import traceback

# APP DETAILS
VERSION = "1.1.2"
APP_NAME = "FitFetch"
OWNER = "BrainlessDip"


class CloudflareBypass:
    """Handles Cloudflare protected pages with cloudscraper and retry strategy"""

    def __init__(self, threads=10):
        self.threads = threads
        self.local = threading.local()
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def _createSession(self):
        scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )
        scraper.headers.update({"User-Agent": self.user_agent})

        retryStrategy = Retry(
            total=5,
            backoff_factor=1.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )

        adapter = HTTPAdapter(
            max_retries=retryStrategy, pool_connections=100, pool_maxsize=100
        )

        scraper.mount("http://", adapter)
        scraper.mount("https://", adapter)

        return scraper

    def _getSession(self):
        if not hasattr(self.local, "session"):
            self.local.session = self._createSession()
        return self.local.session

    def fetch(self, url, method="GET"):
        """Fetch a single URL"""
        session = self._getSession()

        try:
            r = (
                session.get(url, timeout=30, allow_redirects=True)
                if method == "GET"
                else session.post(url, timeout=30, allow_redirects=False)
            )
            return url, r.text, r.status_code, r.headers

        except Exception:
            return url, None, None, None

    def fetchMany(self, urls):
        """Fetch multiple URLs concurrently"""
        results = {}

        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            futures = [executor.submit(self.fetch, url) for url in urls]

            for f in as_completed(futures):
                url, data, status, headers = f.result()
                results[url] = {
                    "content": data,
                    "status": status,
                    "url": url,
                    "headers": headers,
                }

        return results


class CloudflareWorker(QThread):
    """Worker thread for Cloudflare extraction (V1)"""

    status_update = pyqtSignal(str)
    progress_update = pyqtSignal(int)
    link_found = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    extraction_complete = pyqtSignal()

    def __init__(self, links, threads=10, delay=1000):
        super().__init__()
        self.links = links
        self.total_links = 0
        self.threads = threads
        self.delay = delay
        self.cf_bypass = None

    def run(self):
        try:
            self.status_update.emit("Initializing Cloudflare bypass...")
            self.cf_bypass = CloudflareBypass(threads=self.threads)

            self.status_update.emit(f"Processing {len(self.links)} links...")
            self.total_links = len(self.links)

            for i, link in enumerate(self.links, 1):
                self.msleep(self.delay)
                filename = link.split("/")[-1].split("#")[-1]
                file_id = (re.search(r"fuckingfast\.co/([^#/?]+)", link)).group(1)
                part_match = re.search(r"part(\d+)", filename, re.IGNORECASE)
                part_num = part_match.group(1) if part_match else "0"
                _, page_source, status_code, headers = self.cf_bypass.fetch(
                    f"https://fuckingfast.co/f/{file_id}/go", method="POST"
                )
                self.status_update.emit(
                    f"[{i}/{len(self.links)}] Processing {filename} (Status: {status_code}) - (Part: {part_num}) - [{i}/{self.total_links}]"
                )

                if page_source and status_code == 429:
                    retry_after = headers.get("Retry-After")
                    if retry_after:
                        try:
                            retry_seconds = int(retry_after)
                        except Exception:
                            retry_seconds = 60
                    else:
                        retry_seconds = 60

                    self.link_found.emit(
                        f"RATE LIMITED: {filename} - Try again in {retry_seconds} seconds- (Part: {part_num})- [{i}/{self.total_links}]"
                    )
                    self.status_update.emit(
                        f"Rate Limited: {filename} - (Part: {part_num}) - [{i}/{self.total_links}]"
                    )

                elif page_source and status_code == 403:
                    # Check if it's a Cloudflare challenge
                    if (
                        "cf-challenge" in page_source.lower()
                        or "cloudflare" in page_source.lower()
                        or "just a moment" in page_source.lower()
                    ):
                        self.link_found.emit(
                            f"CLOUDFLARE: {filename} - Protected, use V2 - (Part: {part_num}) - [{i}/{self.total_links}]"
                        )
                        self.status_update.emit(
                            f"Cloudflare detected: {filename} - (Part: {part_num}) - [{i}/{self.total_links}]"
                        )
                elif page_source and status_code == 200:
                    # Try to extract link from page source
                    # extracted_url = self._extract_link_from_html(page_source, filename)
                    extracted_url = headers.get("Hx-Redirect")
                    if extracted_url:
                        self.link_found.emit(extracted_url + f"#{filename}")
                        self.status_update.emit(
                            f"Extracted: {filename} - (Part: {part_num}) - [{i}/{self.total_links}]"
                        )
                    else:
                        self.link_found.emit(
                            f"FAILED: {filename} - No direct link found - (Part: {part_num}) - [{i}/{self.total_links}]"
                        )
                        self.status_update.emit(
                            f"Failed: {filename} - (Part: {part_num}) - [{i}/{self.total_links}]"
                        )
                else:
                    self.link_found.emit(
                        f"FAILED: {filename} - Status {status_code} - (Part: {part_num}) - [{i}/{self.total_links}]"
                    )
                    self.status_update.emit(
                        f"Failed: {filename} (Status: {status_code})- (Part: {part_num}) - [{i}/{self.total_links}]"
                    )
                self.progress_update.emit(i)

            self.status_update.emit("Extraction complete (V1)")
            self.extraction_complete.emit()

        except Exception as e:
            self.error_occurred.emit(
                f"Cloudflare error: {str(e)}\n{traceback.format_exc()}"
            )

    def _extract_link_from_html(self, html, filename):
        """Extract the direct link from HTML content"""
        try:
            pattern = r'https?://(?:[a-zA-Z0-9-]+\.)*fuckingfast\.co(?:/[^\s"\'<>]*)?'
            match = re.search(pattern, html)
            if match:
                return match.group(1) if len(match.groups()) > 0 else match.group(0)
            return None
        except Exception:
            return None


class ZendriverWorker(QThread):
    """Worker thread for zendriver extraction (V2)"""

    status_update = pyqtSignal(str)
    progress_update = pyqtSignal(int)
    link_found = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    extraction_complete = pyqtSignal()

    def __init__(self, links, delay=3):
        super().__init__()
        self.links = links
        self.direct_links = []
        self.total_links = 0
        self.delay = delay
        self.browser = None
        self._shutdown_requested = False

    def run(self):
        try:
            asyncio.run(self._async_run())
        except Exception as e:
            self.error_occurred.emit(f"Zendriver error: {type(e).__name__}: {e}")

    async def _async_run(self):
        try:
            self.status_update.emit("Initializing browser (V2)...")
            self.total_links = len(self.links)

            self.browser = await zd.start(
                headless=False,
                browser_args=[
                    "--window-size=500,550",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-extensions",
                    "--disable-sync",
                    "--disable-background-networking",
                    "--disable-popup-blocking",
                ],
            )

            self.status_update.emit(f"Processing {len(self.links)} links...")
            tab = await self.browser.get("https://fuckingfast.co")

            await tab.wait_for_ready_state("complete")

            for i, link in enumerate(self.links, 1):
                filename = link.split("/")[-1].split("#")[-1]
                file_id = (re.search(r"fuckingfast\.co/([^#/?]+)", link)).group(1)
                part_match = re.search(r"part(\d+)", filename, re.IGNORECASE)
                part_num = part_match.group(1) if part_match else "0"
                self.status_update.emit(
                    f"[{i}/{len(self.links)}] Processing {filename} - (Part:: {part_num}) - [{i}/{self.total_links}]"
                )

                try:
                    self.status_update.emit(
                        f"Extracting from {filename}... - (Part:: {part_num}) - [{i}/{self.total_links}]"
                    )
                    if file_id:
                        headers = await tab.evaluate(
                            f'(async()=>Object.fromEntries((await fetch("/f/{file_id}/go",{{method:"POST"}})).headers.entries()))()',
                            await_promise=True,
                        )
                        extracted_url = headers["hx-redirect"]
                        self.direct_links.append(extracted_url)
                        self.link_found.emit(extracted_url + f"#{filename}")
                        self.status_update.emit(
                            f"Extracted: {filename} - (Part: {part_num}) - [{i}/{self.total_links}]"
                        )
                    # elif "rate limited" in page_source.lower():
                    #     self.link_found.emit(
                    #         f"FAILED: {filename} - Rate limited - (Part:: {part_num})"
                    #     )
                    #     self.status_update.emit(
                    #         f"Failed: {filename} - Rate limited - (Part:: {part_num})"
                    #     )
                    else:
                        self.link_found.emit(
                            f"FAILED: {filename} - No direct link found - (Part:: {part_num}) - [{i}/{self.total_links}]"
                        )
                        self.status_update.emit(
                            f"Failed: {filename} - (Part:: {part_num}) - [{i}/{self.total_links}]"
                        )

                except Exception as e:
                    error_msg = str(e)
                    self.link_found.emit(
                        f"ERROR: {filename} - {error_msg} - (Part:: {part_num}) - [{i}/{self.total_links}]"
                    )
                    self.status_update.emit(
                        f"Error: {filename} - {error_msg} - (Part:: {part_num}) - [{i}/{self.total_links}]"
                    )

                self.progress_update.emit(i)

                # Add delay between requests to avoid rate limiting
                if i < len(self.links) and not self._shutdown_requested:
                    delay_sec = self.delay / 1000
                    self.status_update.emit(
                        f"Waiting {delay_sec} seconds before next request... - [{i}/{self.total_links}]"
                    )
                    await asyncio.sleep(delay_sec)

            self.status_update.emit("Extraction complete (V2)")
            self.extraction_complete.emit()

        except Exception as e:
            error_msg = f"Browser error: {type(e).__name__}: {e}"
            self.error_occurred.emit(error_msg)
        finally:
            if self.browser:
                try:
                    self.status_update.emit(
                        f"Closing browser... ({len(self.direct_links)} links)"
                    )
                    self.direct_links.clear()
                    await self.browser.stop()
                except Exception:
                    pass


class FetchWorker(QThread):
    """Worker for fetching links from FitGirl page"""

    status_update = pyqtSignal(str)
    fetch_complete = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            self.status_update.emit("Fetching links from FitGirl...")

            # Use cloudscraper for initial fetch to bypass Cloudflare
            scraper = cloudscraper.create_scraper(
                browser={"browser": "chrome", "platform": "windows", "mobile": False}
            )

            html = scraper.get(
                self.url,
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


class CheckUpdateWorker(QThread):
    """Background worker to check GitHub for latest release.

    Uses urllib.request directly with a short timeout for fast, lightweight checks.
    Emits signals for update found, no update, and errors — all safe to connect
    to UI slots since cross-thread signal delivery is queued by Qt.
    """

    update_found = pyqtSignal(str, str, str, str, str)
    update_error = pyqtSignal(str)
    no_update = pyqtSignal(str, str, str, str)

    NETWORK_TIMEOUT = 8  # seconds

    def __init__(self, owner, repo, current_version, parent=None):
        super().__init__(parent)
        self.owner = owner
        self.repo = repo
        self.current_version = current_version

    def run(self):
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/releases/latest"

        try:
            resp = requests.get(
                url,
                headers={
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": f"{APP_NAME}/{self.current_version}",
                },
                timeout=self.NETWORK_TIMEOUT,
            )
        except requests.ConnectionError:
            self.update_error.emit("Could not connect to GitHub. Check your internet.")
            return
        except requests.Timeout:
            self.update_error.emit("GitHub request timed out. Try again later.")
            return
        except requests.RequestException as e:
            self.update_error.emit(f"Update check failed: {e}")
            return

        if resp.status_code == 404:
            self.update_error.emit("No releases found on GitHub.")
            return
        if resp.status_code == 403:
            self.update_error.emit(
                "GitHub is currently rate limiting update checks. Please try again later."
            )
            return
        if resp.status_code != 200:
            self.update_error.emit(f"GitHub API returned status {resp.status_code}.")
            return

        try:
            data = resp.json()
        except (ValueError, KeyError) as e:
            self.update_error.emit(f"Invalid response from GitHub: {e}")
            return

        tag = data.get("tag_name", "").lstrip("v")
        body = data.get("body", "No changelog available.")
        html_url = data.get("html_url", "")
        published_at = data.get("published_at", "")

        download_url = ""
        for asset in data.get("assets", []):
            name = asset.get("name", "")
            if name.lower().endswith(".exe"):
                download_url = asset.get("browser_download_url", "")
                break

        if self._version_gt(tag, self.current_version):
            self.update_found.emit(tag, body, html_url, published_at, download_url)
        else:
            self.no_update.emit(tag, body, html_url, published_at)

    @staticmethod
    def _version_gt(remote, local):
        """Compare version strings like '1.2.3' > '1.1.1'"""

        def parse(v):
            return tuple(int(x) for x in v.split(".") if x.isdigit())

        try:
            return parse(remote) > parse(local)
        except ValueError, TypeError:
            return False


class UpdateManager(QObject):
    """Manages background and manual update checks.

    Single entry point: check_for_updates(silent=True/False).
    - silent=True  : no UI feedback, errors logged internally, only shows dialog
                     if an update is actually available.
    - silent=False : shows status bar messages, error dialogs, and 'up to date' dialog.

    All UI interaction happens via Qt signals connected to the main window slots.
    """

    # Signals forwarded from the worker — connect these on the main window
    update_available = pyqtSignal(
        str, str, str, str, str
    )  # tag, body, html_url, published_at, download_url
    check_failed = pyqtSignal(str)  # error message
    check_started = pyqtSignal()  # emitted when a check begins

    def __init__(self, owner, repo, current_version, parent=None):
        super().__init__(parent)
        self.owner = owner
        self.repo = repo
        self.current_version = current_version
        self._worker = None

    def check_for_updates(self, silent=True):
        """Start an update check.

        Args:
            silent: If True, suppresses all UI except the update-available dialog.
                    If False, shows loading messages, error dialogs, and up-to-date dialog.
        """
        # Prevent overlapping checks
        if self._worker and self._worker.isRunning():
            return

        self._silent = silent
        self.check_started.emit()

        self._worker = CheckUpdateWorker(
            self.owner, self.repo, self.current_version, parent=None
        )
        self._worker.update_found.connect(self._on_update_found)
        self._worker.update_error.connect(self._on_check_error)
        self._worker.no_update.connect(self._on_no_update)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def _on_worker_finished(self):
        """Clean up worker reference after thread completes."""
        self._worker = None

    def _on_update_found(self, tag, body, html_url, published_at, download_url):
        """An update was found — always show the dialog (silent or not)."""
        self.update_available.emit(tag, body, html_url, published_at, download_url)

    def _on_check_error(self, message):
        """Handle check failure based on silent mode."""
        if self._silent:
            # Silent mode: swallow the error, do not show any dialog or status
            return
        self.check_failed.emit(message)

    def _on_no_update(self, tag, body, html_url, published_at):
        """No update found — only show dialog in manual (non-silent) mode."""
        if self._silent:
            return
        # Emit a special signal or let the main window handle it directly
        # We store the data and let the main window decide
        self.no_update_found.emit(tag, body, html_url, published_at)

    # Additional signal for "no update" in manual mode
    no_update_found = pyqtSignal(str, str, str, str)


class SettingsDialog(QDialog):
    """Dialog for customizing delay settings"""

    def __init__(self, v1_delay, v2_delay, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings - FitFetch")
        self.setMinimumWidth(400)
        self.setModal(True)

        layout = QVBoxLayout(self)

        # V1 Delay setting
        v1_group = ModernGroupBox("V1 (Cloudflare) Extraction")
        v1_layout = QFormLayout(v1_group)

        self.v1_delay_spin = QSpinBox()
        self.v1_delay_spin.setRange(0, 30000)
        self.v1_delay_spin.setSingleStep(100)
        self.v1_delay_spin.setValue(v1_delay)
        self.v1_delay_spin.setSuffix(" ms")
        self.v1_delay_spin.setToolTip(
            "Delay between each V1 (Cloudflare) request in milliseconds.\n"
            "Higher values reduce rate limiting but slow extraction.\n"
            "Default: 1000 ms (1 second)"
        )
        v1_layout.addRow("Request Delay:", self.v1_delay_spin)

        v1_desc = QLabel(
            "Time to wait between each link request during V1 extraction.\n"
            "Increase if you get rate-limited frequently."
        )
        v1_desc.setStyleSheet(f"color: {ModernStyle.TEXT_SECONDARY}; font-size: 11px;")
        v1_desc.setWordWrap(True)
        v1_layout.addRow("", v1_desc)

        layout.addWidget(v1_group)

        # V2 Delay setting
        v2_group = ModernGroupBox("V2 (Browser) Extraction")
        v2_layout = QFormLayout(v2_group)

        self.v2_delay_spin = QSpinBox()
        self.v2_delay_spin.setRange(0, 30000)
        self.v2_delay_spin.setSingleStep(100)
        self.v2_delay_spin.setValue(v2_delay)
        self.v2_delay_spin.setSuffix(" ms")
        self.v2_delay_spin.setToolTip(
            "Delay between each V2 (Browser) request to avoid rate limiting.\n"
            "Higher values reduce rate limiting but slow extraction.\n"
            "Default: 2000 ms (2 seconds)"
        )
        v2_layout.addRow("Request Delay:", self.v2_delay_spin)

        v2_desc = QLabel(
            "Time to wait between each link request during V2 extraction.\n"
            "Increase if you get rate-limited frequently."
        )
        v2_desc.setStyleSheet(f"color: {ModernStyle.TEXT_SECONDARY}; font-size: 11px;")
        v2_desc.setWordWrap(True)
        v2_layout.addRow("", v2_desc)

        layout.addWidget(v2_group)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_v1_delay(self):
        return self.v1_delay_spin.value()

    def get_v2_delay(self):
        return self.v2_delay_spin.value()


class FitFetchApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.checkboxes = []
        self.checkbox_links = {}
        self.checkbox_widgets = []
        self.links = []
        self.direct_links = []
        self.current_file = None
        self.worker = None
        self.extract_worker = None

        # Delay settings (defaults)
        self.v1_delay = 1000  # milliseconds
        self.v2_delay = 1000  # milliseconds

        self.init_ui()
        self.apply_modern_style()

        # Update manager — handles both silent startup and manual checks
        self._update_manager = UpdateManager(OWNER, APP_NAME.lower(), VERSION, self)
        self._update_manager.update_available.connect(self._on_update_found)
        self._update_manager.check_failed.connect(self._on_update_error)
        self._update_manager.no_update_found.connect(self._on_no_update)

        # Flag to ensure the startup update dialog only appears once per session
        self._startup_update_shown = False

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
        fetch_action.triggered.connect(self.start_fetch)
        file_menu.addAction(fetch_action)

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

        delays_action = QAction("Delays...", self)
        delays_action.triggered.connect(self.open_settings)
        settings_menu.addAction(delays_action)

        settings_menu.addSeparator()

        check_update_action = QAction("Check for Updates...", self)
        check_update_action.triggered.connect(self.check_for_updates)
        settings_menu.addAction(check_update_action)

        # Help menu
        help_menu = menubar.addMenu("Help")

        how_to_use_action = QAction("How to Use", self)
        how_to_use_action.triggered.connect(self.show_help)
        help_menu.addAction(how_to_use_action)

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
        fetch_btn.triggered.connect(self.start_fetch)
        toolbar.addAction(fetch_btn)

        extract_v1_btn = QAction("Extract V1", self)
        extract_v1_btn.triggered.connect(lambda: self.start_extraction(method="v1"))
        toolbar.addAction(extract_v1_btn)

        extract_v2_btn = QAction("Extract V2", self)
        extract_v2_btn.triggered.connect(lambda: self.start_extraction(method="v2"))
        toolbar.addAction(extract_v2_btn)

        toolbar.addSeparator()

        select_all_btn = QAction("Select All", self)
        select_all_btn.triggered.connect(self.select_all)
        toolbar.addAction(select_all_btn)

        deselect_all_btn = QAction("Deselect All", self)
        deselect_all_btn.triggered.connect(self.deselect_all)
        toolbar.addAction(deselect_all_btn)

        toolbar.addSeparator()

        save_btn = QAction("Save", self)
        save_btn.triggered.connect(self.save_links)
        toolbar.addAction(save_btn)

        copy_btn = QAction("Copy", self)
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
        self.url_input.returnPressed.connect(self.start_fetch)

        self.paste_btn = QPushButton("Paste")
        self.paste_btn.setProperty("primary", True)
        self.paste_btn.clicked.connect(self.paste_from_clipboard)
        self.paste_btn.setFixedWidth(80)
        self.paste_btn.setFixedHeight(32)

        self.fetch_btn = QPushButton("Fetch")
        self.fetch_btn.setProperty("primary", True)
        self.fetch_btn.clicked.connect(self.start_fetch)
        self.fetch_btn.setFixedWidth(80)
        self.fetch_btn.setFixedHeight(32)

        url_layout.addWidget(self.url_input)
        url_layout.addWidget(self.paste_btn)
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

        self.extract_v1_btn = QPushButton("Extract V1")
        self.extract_v1_btn.setProperty("primary", True)
        self.extract_v1_btn.clicked.connect(lambda: self.start_extraction(method="v1"))
        self.extract_v1_btn.setEnabled(False)
        self.extract_v1_btn.setFixedHeight(32)
        self.extract_v1_btn.setFixedWidth(100)

        self.extract_v2_btn = QPushButton("Extract V2")
        self.extract_v2_btn.setProperty("primary", True)
        self.extract_v2_btn.clicked.connect(lambda: self.start_extraction(method="v2"))
        self.extract_v2_btn.setEnabled(False)
        self.extract_v2_btn.setFixedHeight(32)
        self.extract_v2_btn.setFixedWidth(100)

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

    def paste_from_clipboard(self):
        """Paste URL from clipboard into the input field with validation"""
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()

        if not text:
            self.statusBar().showMessage("Clipboard is empty", 3000)
            return

        if self._is_valid_fitgirl_url(text):
            self.url_input.setText(text)
            self.statusBar().showMessage(
                "Valid FitGirl URL pasted from clipboard", 3000
            )
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

    def _is_valid_fitgirl_url(self, url):
        """Validate if the URL is a proper FitGirl repack URL"""
        if not url:
            return False

        fitgirl_patterns = [
            r"^https?://fitgirl-repacks\.site/[a-zA-Z0-9\-_]+/?$",
            r"^https?://www\.fitgirl-repacks\.site/[a-zA-Z0-9\-_]+/?$",
            r"^https?://fitgirl-repacks\.site/[a-zA-Z0-9\-_]+/[a-zA-Z0-9\-_/]*$",
            r"^https?://www\.fitgirl-repacks\.site/[a-zA-Z0-9\-_]+/[a-zA-Z0-9\-_/]*$",
        ]

        for pattern in fitgirl_patterns:
            if re.match(pattern, url, re.IGNORECASE):
                return True

        return False

    def show_about(self):
        about_text = f"""
            <h2>{APP_NAME} v{VERSION}</h2>

            <p>
              A modern desktop application for extracting direct download links
              from FitGirl Repack pages quickly and efficiently.
            </p>

            <h3>Features</h3>
            <ul>
              <li><b>V1 (Cloudflare):</b> Fast concurrent extraction using cloudscraper</li>
              <li><b>V2 (Browser):</b> Fallback using zendriver for Cloudflare challenges</li>
              <li>Modern dark-themed interface</li>
              <li>Select or deselect individual parts</li>
              <li>One-click clipboard copying</li>
              <li>Export links to a text file</li>
              <li>Fast and reliable extraction</li>
            </ul>

            <p>
              Built with <b>PyQt6</b>, <b>cloudscraper</b> and <b>zendriver</b>.
            </p>

            <hr>

            <p>
              <b>Developer:</b> Dip Dey
            </p>

            <p>
              <a href="https://github.com/BrainlessDip/fitfetch">
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

    def show_help(self):
        help_text = f"""
            <h2>{APP_NAME} - How to Use</h2>

            <h3>Step 1: Fetch Links</h3>
            <ol>
              <li>Paste a FitGirl repack URL into the input field (or click <b>Paste</b> to paste from clipboard)</li>
              <li>Click <b>Fetch</b> or press <b>Enter</b></li>
              <li>The app will scrape all download links from the page</li>
              <li>Links appear as checkboxes in the <b>Parts</b> section</li>
            </ol>

            <h3>Step 2: Select Parts</h3>
            <ul>
              <li>All parts are selected by default</li>
              <li>Use <b>Select All</b> / <b>Deselect All</b> to toggle</li>
              <li>Click individual checkboxes or part names to select/deselect specific parts</li>
            </ul>

            <h3>Step 3: Extract Direct Links</h3>
            <ul>
              <li><b>Extract V1 (Cloudflare):</b> Fast method using cloudscraper. Works when the site is not heavily Cloudflare-protected.</li>
              <li><b>Extract V2 (Browser):</b> Uses a real browser (zendriver) to bypass Cloudflare challenges. Slower but more reliable for protected pages.</li>
            </ul>
            <p>Choose V2 if V1 fails with Cloudflare errors.</p>

            <h3>Step 4: Save or Copy Links</h3>
            <ul>
              <li>Extracted direct download links appear in the <b>Links</b> section</li>
              <li><b>Copy:</b> Copy all links to clipboard</li>
              <li><b>Save:</b> Export links to a text file</li>
            </ul>

            <hr>

            <h3>Settings</h3>
            <p>Go to <b>Settings &gt; Delays...</b> to customize extraction delays:</p>
            <ul>
              <li><b>V1 Request Delay:</b> Time between each Cloudflare request (default: 1000 ms). Increase if rate-limited.</li>
              <li><b>V2 Request Delay:</b> Time between each browser request (default: 1000 ms). Increase if rate-limited.</li>
            </ul>

            <hr>

            <h3>Tips</h3>
            <ul>
              <li>Use V1 first for speed; switch to V2 only if V1 fails</li>
              <li>If you're extracting just one file or using the app occasionally, set the V1 or V2 delay to <b>0 ms</b> for maximum speed.</li>
              <li>If you get rate-limited, increase the V1 delay in Settings</li>
              <li>The V2 browser window is real - don't close it during extraction</li>
              <li>You can paste a URL directly by clicking <b>Paste</b></li>
            </ul>
            """
        msgBox = QMessageBox(self)
        msgBox.setWindowTitle(f"{APP_NAME} - How to Use")
        msgBox.setTextFormat(Qt.TextFormat.RichText)
        msgBox.setText(help_text)
        msgBox.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        msgBox.setMinimumWidth(500)
        msgBox.exec()

    def open_settings(self):
        dialog = SettingsDialog(self.v1_delay, self.v2_delay, self)
        if dialog.exec():
            self.v1_delay = dialog.get_v1_delay()
            self.v2_delay = dialog.get_v2_delay()
            self.statusBar().showMessage(
                f"Settings updated: V1 delay={self.v1_delay}ms, V2 delay={self.v2_delay / 1000}s",
                3000,
            )

    def check_for_updates(self):
        """Manual 'Check for Updates' from the Settings menu — non-silent."""
        self.statusBar().showMessage("Checking for updates...", 5000)
        self._update_manager.check_for_updates(silent=False)

    def _on_update_found(self, tag, body, html_url, published_at, download_url):
        date_str = ""
        if published_at:
            try:
                dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                date_str = dt.strftime("%Y-%m-%d")
            except ValueError, TypeError:
                date_str = published_at[:10]

        dlg = QDialog(self)
        dlg.setWindowTitle("Update Available")
        dlg.setFixedSize(520, 380)
        dlg.setStyleSheet(f"""
            QDialog {{
                background-color: {ModernStyle.BG_PRIMARY};
                color: {ModernStyle.TEXT_PRIMARY};
            }}
            QLabel {{
                color: {ModernStyle.TEXT_PRIMARY};
            }}
        """)

        layout = QVBoxLayout(dlg)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel(
            f"<h3 style='color: {ModernStyle.ACCENT}; margin:0;'>Update Available: v{tag}</h3>"
        )
        title.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(title)

        info = QLabel(
            f"<p style='color: {ModernStyle.TEXT_SECONDARY};'>"
            f"Current version: <b>{VERSION}</b> &rarr; New version: <b>{tag}</b></p>"
        )
        info.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(info)

        if date_str:
            date_label = QLabel(
                f"<p style='color: {ModernStyle.TEXT_MUTED};'>Released: {date_str}</p>"
            )
            date_label.setTextFormat(Qt.TextFormat.RichText)
            layout.addWidget(date_label)

        btn_style = f"""
            QPushButton {{
                background-color: {ModernStyle.BG_TERTIARY};
                color: {ModernStyle.TEXT_PRIMARY};
                border: 1px solid {ModernStyle.BORDER};
                border-radius: {ModernStyle.RADIUS}px;
                padding: 6px 16px;
                min-width: 60px;
            }}
            QPushButton:hover {{
                background-color: {ModernStyle.BG_HOVER};
                border-color: {ModernStyle.ACCENT};
            }}
            QPushButton:pressed {{
                background-color: {ModernStyle.ACCENT_PRESSED};
            }}
        """

        details_text = body if body else "No changelog available."
        details_label = QLabel(details_text)
        details_label.setWordWrap(True)
        details_label.setStyleSheet(
            f"color: {ModernStyle.TEXT_SECONDARY}; background-color: {ModernStyle.BG_SECONDARY}; border: 1px solid {ModernStyle.BORDER}; border-radius: {ModernStyle.RADIUS}px; padding: 8px;"
        )
        layout.addWidget(details_label)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        ok_btn = QPushButton("OK")
        ok_btn.setStyleSheet(btn_style)
        ok_btn.clicked.connect(dlg.accept)
        btn_layout.addWidget(ok_btn)

        view_btn = QPushButton("View Page")
        view_btn.setStyleSheet(btn_style)
        view_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(html_url)))
        btn_layout.addWidget(view_btn)

        download_btn = QPushButton("Download")
        download_btn.setStyleSheet(btn_style)

        def open_download():
            if download_url:
                QDesktopServices.openUrl(QUrl(download_url))
            else:
                QDesktopServices.openUrl(QUrl(html_url))

        download_btn.clicked.connect(open_download)
        btn_layout.addWidget(download_btn)

        layout.addLayout(btn_layout)

        dlg.setMinimumSize(520, 300)
        dlg.resize(520, 380)
        dlg.exec()

    def _on_update_error(self, message):
        QMessageBox.warning(self, "Update Check Failed", message)

    def _on_no_update(self, tag, body, html_url, published_at):
        date_str = ""
        if published_at:
            try:
                dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                date_str = dt.strftime("%Y-%m-%d")
            except ValueError, TypeError:
                date_str = published_at[:10]

        dlg = QDialog(self)
        dlg.setWindowTitle("Version Info")
        dlg.setStyleSheet(f"""
            QDialog {{
                background-color: {ModernStyle.BG_PRIMARY};
                color: {ModernStyle.TEXT_PRIMARY};
            }}
            QLabel {{
                color: {ModernStyle.TEXT_PRIMARY};
            }}
        """)

        layout = QVBoxLayout(dlg)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel(
            f"<h3 style='color: {ModernStyle.ACCENT}; margin:0;'>Up to Date: v{VERSION}</h3>"
        )
        title.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(title)

        info = QLabel(
            f"<p style='color: {ModernStyle.TEXT_SECONDARY};'>"
            f"Current version: <b>{VERSION}</b> &rarr; Latest: <b>{tag}</b></p>"
        )
        info.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(info)

        if date_str:
            date_label = QLabel(
                f"<p style='color: {ModernStyle.TEXT_MUTED};'>Released: {date_str}</p>"
            )
            date_label.setTextFormat(Qt.TextFormat.RichText)
            layout.addWidget(date_label)

        btn_style = f"""
            QPushButton {{
                background-color: {ModernStyle.BG_TERTIARY};
                color: {ModernStyle.TEXT_PRIMARY};
                border: 1px solid {ModernStyle.BORDER};
                border-radius: {ModernStyle.RADIUS}px;
                padding: 6px 16px;
                min-width: 60px;
            }}
            QPushButton:hover {{
                background-color: {ModernStyle.BG_HOVER};
                border-color: {ModernStyle.ACCENT};
            }}
            QPushButton:pressed {{
                background-color: {ModernStyle.ACCENT_PRESSED};
            }}
        """

        details_text = body if body else "No changelog available."
        details_label = QLabel(details_text)
        details_label.setWordWrap(True)
        details_label.setStyleSheet(
            f"color: {ModernStyle.TEXT_SECONDARY}; background-color: {ModernStyle.BG_SECONDARY}; border: 1px solid {ModernStyle.BORDER}; border-radius: {ModernStyle.RADIUS}px; padding: 8px;"
        )
        layout.addWidget(details_label)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        ok_btn = QPushButton("OK")
        ok_btn.setStyleSheet(btn_style)
        ok_btn.clicked.connect(dlg.accept)
        btn_layout.addWidget(ok_btn)

        view_btn = QPushButton("View Page")
        view_btn.setStyleSheet(btn_style)
        view_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(html_url)))
        btn_layout.addWidget(view_btn)

        layout.addLayout(btn_layout)

        dlg.setMinimumSize(520, 300)
        dlg.resize(520, 380)
        dlg.exec()

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

    def add_output(self, text: str):
        self.output_text.append(text)
        cursor = self.output_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.output_text.setTextCursor(cursor)
        if text.startswith("http"):
            self.direct_links.append(text)
        self.update_link_count()

    def clear_checkboxes(self):
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.checkboxes.clear()
        self.checkbox_links.clear()
        self.checkbox_widgets.clear()
        self.direct_links.clear()
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
            except Exception:
                return 0

        sorted_links = sorted(links, key=extract_number)

        for idx, link in enumerate(sorted_links, 1):
            filename = link.split("/")[-1].split("#")[-1]
            part_match = re.search(r"part(\d+)", filename, re.IGNORECASE)
            part_num = part_match.group(1) if part_match else "0"

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
                lambda state, ref=link: self.on_checkbox_changed(ref, state)
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
        self.extract_v1_btn.setEnabled(True)
        self.extract_v2_btn.setEnabled(True)

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
        self.extract_v1_btn.setEnabled(False)
        self.extract_v2_btn.setEnabled(False)
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

    def start_extraction(self, method="v1"):
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

        if method == "v1":
            self.extract_worker = CloudflareWorker(
                selected, threads=10, delay=self.v1_delay
            )
            self.update_status("Starting V1 extraction (Cloudflare bypass)...")
        else:
            self.extract_worker = ZendriverWorker(selected, delay=self.v2_delay)
            self.update_status("Starting V2 extraction (Browser)...")

        self.extract_worker.status_update.connect(self.update_status)
        self.extract_worker.progress_update.connect(self.progress_bar.setValue)
        self.extract_worker.link_found.connect(self.add_output)
        self.extract_worker.error_occurred.connect(self.on_extract_error)
        self.extract_worker.extraction_complete.connect(self.on_extraction_complete)
        self.extract_worker.start()

    def on_extract_error(self, error_msg):
        self.update_status(f"Error: {error_msg}")
        self.fetch_btn.setEnabled(True)
        self.extract_v1_btn.setEnabled(True)
        self.extract_v2_btn.setEnabled(True)
        QMessageBox.critical(self, "Error", f"Extraction error:\n{error_msg}")

    def on_extraction_complete(self):
        self.fetch_btn.setEnabled(True)
        self.extract_v1_btn.setEnabled(True)
        self.extract_v2_btn.setEnabled(True)
        self.update_status(f"Extraction complete ({len(self.direct_links)} links)")
        self.direct_links.clear()
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

    def showEvent(self, event):
        """Trigger a silent background update check after the window is fully visible."""
        super().showEvent(event)
        # Delay slightly so the UI is fully rendered before starting the network call
        QTimer.singleShot(1500, self._startup_update_check)

    def _startup_update_check(self):
        """Run the silent update check on startup (once per launch)."""
        if self._startup_update_shown:
            return
        self._startup_update_shown = True
        self._update_manager.check_for_updates(silent=True)

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

        # Stop the update check worker if still running
        if self._update_manager._worker and self._update_manager._worker.isRunning():
            self._update_manager._worker.quit()
            self._update_manager._worker.wait(3000)

        if hasattr(self, "worker") and self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        if (
            hasattr(self, "extract_worker")
            and self.extract_worker
            and self.extract_worker.isRunning()
        ):
            self.extract_worker._shutdown_requested = True
            self.extract_worker.wait(5000)
            if self.extract_worker.isRunning():
                self.extract_worker.terminate()
                self.extract_worker.wait()

        event.accept()


def resource_path(relative_path):
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle(QStyleFactory.create("Fusion"))
    app.setWindowIcon(QIcon(resource_path("favicon.ico")))

    window = FitFetchApp()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
