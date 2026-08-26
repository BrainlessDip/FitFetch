"""All dialog classes for FitFetch."""

from __future__ import annotations

from datetime import datetime

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
)

from ..constants import APP_NAME, VERSION
from ..config import MAX_WINDOW_COUNT, MIN_WINDOW_COUNT
from .styles import ModernStyle
from .widgets import ModernGroupBox


# ---------------------------------------------------------------------------
# Settings dialog
# ---------------------------------------------------------------------------


class SettingsDialog(QDialog):
    """Dialog for customising V1 / V2 extraction delay settings."""

    def __init__(self, v1_delay: int, v2_delay: int, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings - FitFetch")
        self.setMinimumWidth(400)
        self.setModal(True)

        layout = QVBoxLayout(self)

        # V1 Delay
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
            "Default: 0 ms (0 second)"
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

        # V2 Delay
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

    def get_v1_delay(self) -> int:
        return self.v1_delay_spin.value()

    def get_v2_delay(self) -> int:
        return self.v2_delay_spin.value()


# ---------------------------------------------------------------------------
# Multi-window settings dialog
# ---------------------------------------------------------------------------


class MultiWindowSettingsDialog(QDialog):
    """Dialog for customising the number of parallel V2 extraction windows."""

    def __init__(
        self,
        window_count: int = 2,
        random_positions: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Multi-Window Settings - FitFetch")
        self.setMinimumWidth(400)
        self.setModal(True)

        layout = QVBoxLayout(self)

        mw_group = ModernGroupBox("Multi-Window Settings")
        mw_layout = QFormLayout(mw_group)

        self.window_count_spin = QSpinBox()
        self.window_count_spin.setRange(MIN_WINDOW_COUNT, MAX_WINDOW_COUNT)
        self.window_count_spin.setSingleStep(1)
        self.window_count_spin.setValue(window_count)
        self.window_count_spin.setToolTip(
            "Number of independent browser windows used during V2 extraction.\n"
            "Each window runs in its own isolated worker and profile.\n"
            f"Range: {MIN_WINDOW_COUNT} - {MAX_WINDOW_COUNT}. Default: 2."
        )
        mw_layout.addRow("Number of Extraction Windows:", self.window_count_spin)

        self.random_positions_check = QCheckBox("Spawn windows at random positions")
        self.random_positions_check.setChecked(random_positions)
        self.random_positions_check.setToolTip(
            "When enabled, extraction windows are placed at random positions\n"
            "on the available screen instead of stacking at the left edge."
        )
        mw_layout.addRow("", self.random_positions_check)

        mw_warning = QLabel(
            "Make sure you're rich enough to increase the value — each window "
            "uses additional CPU, RAM, and browser resources."
        )
        mw_warning.setWordWrap(True)
        mw_warning.setStyleSheet(f"color: {ModernStyle.WARNING}; font-size: 11px;")
        mw_layout.addRow("", mw_warning)

        layout.addWidget(mw_group)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_window_count(self) -> int:
        return self.window_count_spin.value()

    def get_random_positions(self) -> bool:
        return self.random_positions_check.isChecked()


# ---------------------------------------------------------------------------
# Browser settings dialog
# ---------------------------------------------------------------------------


class BrowserSettingsDialog(QDialog):
    """Informational dialog showing detected browser details."""

    def __init__(
        self,
        detected: dict[str, str],
        selected: str | None,
        active_path: str | None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Browser Settings")
        self.setModal(True)

        selected_text = selected if selected else "Auto Detect"
        detected_text = ", ".join(detected.keys()) if detected else "None found"
        path_text = active_path if active_path else "No browser found"

        if active_path:
            active_name = next(
                (name for name, path in detected.items() if path == active_path),
                "None",
            )
        else:
            active_name = "None"

        if not selected and active_path:
            detail_text = f"Auto-detected: {active_name}"
        elif not selected and not active_path:
            detail_text = "No browser found. Please install Chrome, Edge, or Brave."
        else:
            detail_text = ""

        info_html = f"""
            <h3>Browser (V2)</h3>
            <p><b>Selected:</b> {selected_text}</p>
            <p><b>Detected:</b> {detected_text}</p>
            <p><b>Path:</b><br><span style="color: {"green" if active_path else "red"};">{path_text}</span></p>
            {"<p><i>" + detail_text + "</i></p>" if detail_text else ""}
            <hr>
            <p style="color: gray; font-size: 11px;">
                Change the browser selection using the dropdown next to the Extract buttons.
            </p>
        """

        layout = QVBoxLayout(self)
        msg = QLabel(info_html)
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setWordWrap(True)
        layout.addWidget(msg)

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn, alignment=Qt.AlignmentFlag.AlignRight)


# ---------------------------------------------------------------------------
# Version / update dialogs
# ---------------------------------------------------------------------------


class VersionDialog(QDialog):
    """Reusable dialog for displaying version/update information."""

    def __init__(
        self,
        title: str,
        subtitle: str,
        body: str,
        html_url: str,
        published_at: str | None,
        extra_buttons: list[tuple[str, callable]] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Update Available" if extra_buttons else "Version Info")
        self.setStyleSheet(ModernStyle.dialog_style())

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        title_lbl = QLabel(
            f"<h3 style='color: {ModernStyle.ACCENT}; margin:0;'>{title}</h3>"
        )
        title_lbl.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(title_lbl)

        info_lbl = QLabel(
            f"<p style='color: {ModernStyle.TEXT_SECONDARY};'>{subtitle}</p>"
        )
        info_lbl.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(info_lbl)

        if published_at:
            date_str = _format_date(published_at)
            date_lbl = QLabel(
                f"<p style='color: {ModernStyle.TEXT_MUTED};'>Released: {date_str}</p>"
            )
            date_lbl.setTextFormat(Qt.TextFormat.RichText)
            layout.addWidget(date_lbl)

        details_lbl = QLabel(body if body else "No changelog available.")
        details_lbl.setWordWrap(True)
        details_lbl.setStyleSheet(ModernStyle.details_label_style())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(details_lbl)
        scroll.setStyleSheet(
            f"border: none; background-color: {ModernStyle.BG_SECONDARY};"
        )
        scroll.setMaximumHeight(250)
        layout.addWidget(scroll)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_style = ModernStyle.button_style()

        ok_btn = QPushButton("OK")
        ok_btn.setStyleSheet(btn_style)
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)

        view_btn = QPushButton("View Page")
        view_btn.setStyleSheet(btn_style)
        view_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(html_url)))
        btn_layout.addWidget(view_btn)

        for label, callback in extra_buttons or []:
            btn = QPushButton(label)
            btn.setStyleSheet(btn_style)
            btn.clicked.connect(callback)
            btn_layout.addWidget(btn)

        layout.addLayout(btn_layout)

        self.setMinimumSize(520, 350)
        self.resize(520, 430)


# ---------------------------------------------------------------------------
# About / Help dialogs
# ---------------------------------------------------------------------------


class AboutDialog(QMessageBox):
    """About FitFetch dialog."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
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
        self.setWindowTitle(f"About {APP_NAME}")
        self.setTextFormat(Qt.TextFormat.RichText)
        self.setText(about_text)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)


class HelpDialog(QMessageBox):
    """How-to-use dialog."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
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
            <p>Go to <b>Settings &gt; Delays...</b> to customise extraction delays:</p>
            <ul>
              <li><b>V1 Request Delay:</b> Time between each Cloudflare request (default: 0 ms). Increase if rate-limited.</li>
              <li><b>V2 Request Delay:</b> Time between each browser request (default: 0 ms). Increase if rate-limited.</li>
            </ul>
            <p>Go to <b>Settings &gt; Multi-Window...</b> to choose how many independent
            browser windows run in parallel during V2 extraction (default: 1).
            Each window uses its own isolated browser profile.</p>

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
        self.setWindowTitle(f"{APP_NAME} - How to Use")
        self.setTextFormat(Qt.TextFormat.RichText)
        self.setText(help_text)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.setMinimumWidth(500)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _format_date(published_at: str) -> str:
    """Best-effort formatting of an ISO date string."""
    try:
        dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return published_at[:10] if len(published_at) >= 10 else published_at
