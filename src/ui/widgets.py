"""Reusable custom widget subclasses."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QCheckBox, QGroupBox

from .styles import ModernStyle


class ClickableCheckBox(QCheckBox):
    """A checkbox that toggles on left-click anywhere on the widget."""

    def __init__(self, text: str, parent=None) -> None:
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle()
            event.accept()
        else:
            super().mousePressEvent(event)


class ModernGroupBox(QGroupBox):
    """A styled group box matching the dark theme."""

    def __init__(self, title: str, parent=None) -> None:
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
