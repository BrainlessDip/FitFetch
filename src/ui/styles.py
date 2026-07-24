"""Modern dark theme constants and centralised stylesheet helpers."""

from __future__ import annotations


class ModernStyle:
    """Dark-theme colour palette, sizes, and stylesheet generators."""

    # -- Colours -------------------------------------------------------------
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

    ACCENT = "#3B82F6"
    ACCENT_HOVER = "#2563EB"
    ACCENT_PRESSED = "#1D4ED8"

    SUCCESS = "#3fb950"
    WARNING = "#d29922"
    ERROR = "#f85149"

    # -- Sizes ---------------------------------------------------------------
    PADDING_SMALL = 4
    PADDING_MEDIUM = 8
    PADDING_LARGE = 12
    RADIUS = 6
    FONT_SIZE = 12
    FONT_SMALL = 11

    # -----------------------------------------------------------------------
    # Stylesheet generators
    # -----------------------------------------------------------------------

    @classmethod
    def button_style(cls) -> str:
        return f"""
            QPushButton {{
                background-color: {cls.BG_TERTIARY};
                color: {cls.TEXT_PRIMARY};
                border: 1px solid {cls.BORDER};
                border-radius: {cls.RADIUS}px;
                padding: 6px 16px;
                min-width: 60px;
            }}
            QPushButton:hover {{
                background-color: {cls.BG_HOVER};
                border-color: {cls.BORDER_ACTIVE};
            }}
            QPushButton:pressed {{
                background-color: {cls.BG_ACTIVE};
                padding-top: 7px;
                padding-bottom: 5px;
            }}
        """

    @classmethod
    def card_button_style(cls) -> str:
        return f"""
            QPushButton {{
                background-color: {cls.BG_TERTIARY};
                color: {cls.TEXT_PRIMARY};
                border: 1px solid {cls.BORDER};
                border-radius: 6px;
                padding: 5px 16px;
                font-size: 11px;
                font-weight: 500;
                min-width: 60px;
            }}
            QPushButton:hover {{
                background-color: {cls.BG_HOVER};
                border-color: {cls.BORDER_ACTIVE};
                color: white;
            }}
            QPushButton:pressed {{
                background-color: {cls.BG_ACTIVE};
                padding-top: 6px;
                padding-bottom: 4px;
            }}
        """

    @classmethod
    def dialog_style(cls) -> str:
        return f"""
            QDialog {{
                background-color: {cls.BG_PRIMARY};
                color: {cls.TEXT_PRIMARY};
            }}
            QLabel {{ color: {cls.TEXT_PRIMARY}; }}
        """

    @classmethod
    def details_label_style(cls) -> str:
        return (
            f"color: {cls.TEXT_SECONDARY}; "
            f"background-color: {cls.BG_SECONDARY}; "
            f"border: 1px solid {cls.BORDER}; "
            f"border-radius: {cls.RADIUS}px; "
            f"padding: 8px;"
        )

    @classmethod
    def header_label_style(cls) -> str:
        return f"font-weight: 600; color: {cls.TEXT_SECONDARY}; font-size: 11px;"

    @classmethod
    def muted_label_style(cls) -> str:
        return f"color: {cls.TEXT_MUTED}; font-size: 11px;"

    @classmethod
    def combobox_style(cls) -> str:
        return f"""
            QComboBox {{
                background-color: {cls.BG_TERTIARY};
                color: {cls.TEXT_PRIMARY};
                border: 1px solid {cls.BORDER};
                border-radius: {cls.RADIUS}px;
                padding: 6px 12px;
                padding-right: 30px;
                font-size: {cls.FONT_SMALL}px;
                font-weight: 500;
                min-height: 18px;
            }}
            QComboBox:hover {{
                background-color: {cls.BG_HOVER};
                border-color: {cls.BORDER_ACTIVE};
            }}
            QComboBox:focus {{
                border-color: {cls.ACCENT};
                background-color: {cls.BG_HOVER};
            }}
            QComboBox:pressed {{
                background-color: {cls.BG_ACTIVE};
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 28px;
                border: none;
                border-left: 1px solid {cls.BORDER};
                border-top-right-radius: {cls.RADIUS}px;
                border-bottom-right-radius: {cls.RADIUS}px;
                background-color: transparent;
            }}
            QComboBox::down-arrow {{
                image: none;
                border: none;
                width: 0;
                height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {cls.TEXT_SECONDARY};
                margin-right: 8px;
            }}
            QComboBox::down-arrow:hover {{
                border-top-color: {cls.TEXT_PRIMARY};
            }}
            QComboBox:on {{
                background-color: {cls.BG_ACTIVE};
                border-color: {cls.ACCENT};
            }}
            QComboBox:on QComboBox::drop-down {{
                border-left-color: {cls.ACCENT};
            }}
            QComboBox QAbstractItemView {{
                background-color: {cls.BG_SECONDARY};
                color: {cls.TEXT_PRIMARY};
                border: 1px solid {cls.BORDER_ACTIVE};
                border-radius: {cls.RADIUS}px;
                padding: 4px 0px;
                selection-background-color: {cls.ACCENT};
                selection-color: white;
                outline: none;
            }}
            QComboBox QAbstractItemView::item {{
                padding: 8px 14px;
                min-height: 20px;
                border: none;
                border-radius: 0px;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: {cls.BG_HOVER};
                color: {cls.TEXT_PRIMARY};
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: {cls.ACCENT};
                color: white;
            }}
        """

    @classmethod
    def toolbar_style(cls) -> str:
        return f"""
            QToolBar {{
                background-color: {cls.BG_SECONDARY};
                border: none;
                border-bottom: 1px solid {cls.BORDER};
                padding: 6px 8px;
                spacing: 4px;
                margin: 0px;
            }}
            QToolBar::separator {{
                background-color: {cls.BORDER};
                width: 1px;
                height: 20px;
                margin: 4px 6px;
            }}
            QToolBar QToolButton {{
                background-color: transparent;
                color: {cls.TEXT_PRIMARY};
                border: 1px solid transparent;
                border-radius: {cls.RADIUS}px;
                padding: 6px 12px;
                font-size: {cls.FONT_SMALL}px;
                font-weight: 500;
                min-height: 20px;
                margin: 0px 2px;
            }}
            QToolBar QToolButton:hover {{
                background-color: {cls.BG_HOVER};
                border-color: {cls.BORDER};
            }}
            QToolBar QToolButton:pressed {{
                background-color: {cls.BG_ACTIVE};
                color: white;
            }}
            QToolBar QToolButton:checked {{
                background-color: {cls.ACCENT};
                color: white;
                border-color: {cls.ACCENT};
            }}
            QToolBar QToolButton:disabled {{
                color: {cls.TEXT_MUTED};
                background-color: transparent;
            }}
        """

    @classmethod
    def application_style(cls) -> str:
        """Return the full application-level stylesheet."""
        return f"""
            QMainWindow {{
                background-color: {cls.BG_PRIMARY};
            }}

            QWidget {{
                background-color: transparent;
                color: {cls.TEXT_PRIMARY};
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                font-size: {cls.FONT_SIZE}px;
            }}

            QPushButton {{
                background-color: {cls.BG_TERTIARY};
                border: 1px solid {cls.BORDER};
                border-radius: {cls.RADIUS}px;
                color: {cls.TEXT_PRIMARY};
                padding: 6px 14px;
                font-weight: 500;
                font-size: {cls.FONT_SMALL}px;
            }}
            QPushButton:hover {{
                background-color: {cls.BG_HOVER};
                border-color: {cls.BORDER_ACTIVE};
            }}
            QPushButton:pressed {{
                background-color: {cls.BG_ACTIVE};
                padding-top: 7px;
                padding-bottom: 5px;
            }}
            QPushButton:disabled {{
                opacity: 0.5;
            }}

            QPushButton[primary="true"] {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {cls.ACCENT}, stop:1 {cls.ACCENT_PRESSED});
                border: none;
                border-radius: 10px;
                color: white;
                font-weight: 600;
                padding: 8px 18px;
            }}
            QPushButton[primary="true"]:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {cls.ACCENT_HOVER}, stop:1 {cls.ACCENT});
            }}
            QPushButton[primary="true"]:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {cls.ACCENT_PRESSED}, stop:1: #153DAB);
            }}
            QPushButton[primary="true"]:disabled {{
                background: #4A5568;
                color: rgba(255,255,255,0.6);
            }}

            QLineEdit {{
                background-color: {cls.BG_TERTIARY};
                border: 1px solid {cls.BORDER};
                border-radius: {cls.RADIUS}px;
                padding: 6px 10px;
                color: {cls.TEXT_PRIMARY};
                selection-background-color: {cls.ACCENT};
                font-size: {cls.FONT_SMALL}px;
            }}
            QLineEdit:focus {{
                border-color: {cls.BORDER_ACTIVE};
            }}
            QLineEdit::placeholder {{
                color: {cls.TEXT_MUTED};
            }}

            QTextEdit {{
                background-color: {cls.BG_PRIMARY};
                border: 1px solid {cls.BORDER};
                border-radius: {cls.RADIUS}px;
                padding: 8px;
                color: {cls.TEXT_PRIMARY};
                selection-background-color: {cls.ACCENT};
                font-family: 'SF Mono', 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                line-height: 1.5;
            }}
            QTextEdit:focus {{
                border-color: {cls.BORDER_ACTIVE};
            }}

            QProgressBar {{
                border: none;
                border-radius: 3px;
                text-align: center;
                height: 20px;
                background-color: {cls.BG_TERTIARY};
                color: {cls.TEXT_SECONDARY};
                font-size: 11px;
                font-weight: 500;
            }}
            QProgressBar::chunk {{
                background-color: {cls.ACCENT};
                border-radius: 3px;
            }}

            QCheckBox {{
                spacing: 8px;
                color: {cls.TEXT_PRIMARY};
                font-size: {cls.FONT_SMALL}px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: 1.5px solid {cls.BORDER};
                background-color: {cls.BG_TERTIARY};
            }}
            QCheckBox::indicator:checked {{
                background-color: {cls.ACCENT};
                border-color: {cls.ACCENT};
            }}
            QCheckBox::indicator:hover {{
                border-color: {cls.BORDER_ACTIVE};
            }}

            QScrollArea {{
                border: none;
                background-color: transparent;
            }}

            QScrollBar:vertical {{
                background-color: {cls.BG_SECONDARY};
                width: 8px;
                border-radius: 4px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {cls.BG_TERTIARY};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {cls.BG_HOVER};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
                height: 0px;
            }}

            QScrollBar:horizontal {{
                background-color: {cls.BG_SECONDARY};
                height: 8px;
                border-radius: 4px;
                margin: 0px;
            }}
            QScrollBar::handle:horizontal {{
                background-color: {cls.BG_TERTIARY};
                border-radius: 4px;
                min-width: 20px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background-color: {cls.BG_HOVER};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                border: none;
                background: none;
                width: 0px;
            }}

            QSplitter::handle {{
                background-color: {cls.BORDER};
                height: 2px;
            }}
            QSplitter::handle:hover {{
                background-color: {cls.BORDER_ACTIVE};
            }}

            QLabel {{
                color: {cls.TEXT_PRIMARY};
                font-size: {cls.FONT_SMALL}px;
            }}

            QMenuBar {{
                background-color: {cls.BG_SECONDARY};
                color: {cls.TEXT_SECONDARY};
                border-bottom: 1px solid {cls.BORDER};
                padding: 2px 0px;
            }}
            QMenuBar::item:selected {{
                background-color: {cls.BG_TERTIARY};
                color: {cls.TEXT_PRIMARY};
            }}

            QMenu {{
                background-color: {cls.BG_SECONDARY};
                color: {cls.TEXT_PRIMARY};
                border: 1px solid {cls.BORDER};
                border-radius: {cls.RADIUS}px;
                padding: 4px 0px;
            }}
            QMenu::item {{
                padding: 6px 30px 6px 20px;
            }}
            QMenu::item:selected {{
                background-color: {cls.BG_TERTIARY};
            }}

            QStatusBar {{
                background-color: {cls.BG_SECONDARY};
                color: {cls.TEXT_SECONDARY};
                border-top: 1px solid {cls.BORDER};
                padding: 2px 8px;
                font-size: 11px;
            }}

            QToolTip {{
                background-color: {cls.BG_SECONDARY};
                color: {cls.TEXT_PRIMARY};
                border: 1px solid {cls.BORDER};
                border-radius: {cls.RADIUS}px;
                padding: 4px 8px;
            }}

            QComboBox {{
                background-color: {cls.BG_TERTIARY};
                color: {cls.TEXT_PRIMARY};
                border: 1px solid {cls.BORDER};
                border-radius: {cls.RADIUS}px;
                padding: 6px 12px;
                padding-right: 30px;
                font-size: {cls.FONT_SMALL}px;
                font-weight: 500;
                min-height: 18px;
            }}
            QComboBox:hover {{
                background-color: {cls.BG_HOVER};
                border-color: {cls.BORDER_ACTIVE};
            }}
            QComboBox:focus {{
                border-color: {cls.ACCENT};
                background-color: {cls.BG_HOVER};
            }}
            QComboBox:pressed {{
                background-color: {cls.BG_ACTIVE};
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 28px;
                border: none;
                border-left: 1px solid {cls.BORDER};
                border-top-right-radius: {cls.RADIUS}px;
                border-bottom-right-radius: {cls.RADIUS}px;
                background-color: transparent;
            }}
            QComboBox::down-arrow {{
                image: none;
                border: none;
                width: 0;
                height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {cls.TEXT_SECONDARY};
                margin-right: 8px;
            }}
            QComboBox::down-arrow:hover {{
                border-top-color: {cls.TEXT_PRIMARY};
            }}
            QComboBox:on {{
                background-color: {cls.BG_ACTIVE};
                border-color: {cls.ACCENT};
            }}
            QComboBox:on QComboBox::drop-down {{
                border-left-color: {cls.ACCENT};
            }}
            QComboBox QAbstractItemView {{
                background-color: {cls.BG_SECONDARY};
                color: {cls.TEXT_PRIMARY};
                border: 1px solid {cls.BORDER_ACTIVE};
                border-radius: {cls.RADIUS}px;
                padding: 4px 0px;
                selection-background-color: {cls.ACCENT};
                selection-color: white;
                outline: none;
            }}
            QComboBox QAbstractItemView::item {{
                padding: 8px 14px;
                min-height: 20px;
                border: none;
                border-radius: 0px;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: {cls.BG_HOVER};
                color: {cls.TEXT_PRIMARY};
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: {cls.ACCENT};
                color: white;
            }}
        """
