"""Advanced file selection dialog — Windows Explorer-like file picker.

Full redesign with grouped view, context menu, keyboard navigation,
smart detection, quick presets, and real-time summary.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

from PyQt6.QtCore import Qt, QEvent, QSize, pyqtSignal
from PyQt6.QtGui import QColor, QKeySequence, QShortcut, QCursor
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .styles import ModernStyle

_FILE_ITEM_ROLE = Qt.ItemDataRole.UserRole


# ═══════════════════════════════════════════════════════════════════════════
# Data model
# ═══════════════════════════════════════════════════════════════════════════

BADGE_COLORS: dict[str, str] = {
    "Main": "#3B82F6",
    "Optional": "#F59E0B",
    "Language Pack": "#10B981",
    "Update": "#A78BFA",
    "Setup": "#6B7280",
    "Bonus": "#EC4899",
    "Crack": "#EF4444",
    "Extras": "#F472B6",
    "DLC": "#8B5CF6",
    "Redistributable": "#78716C",
}

CATEGORY_ICONS: dict[str, str] = {
    "Setup": "\u25B6",
    "Main": "\u25A3",
    "Optional": "\u2606",
    "Language Pack": "\u2699",
    "Update": "\u2191",
    "Bonus": "\u2605",
    "Crack": "\u2694",
    "Extras": "\u2726",
    "DLC": "\u2756",
    "Redistributable": "\u2299",
}

CATEGORY_ORDER: list[str] = [
    "Main",
    "Setup",
    "Language Pack",
    "Optional",
    "Bonus",
    "Crack",
    "Extras",
    "Update",
    "DLC",
    "Redistributable",
]

PRESETS: dict[str, Callable[[FileItem], bool] | None] = {
    "Select Required Only": lambda f: not f.is_optional,
    "Select Everything": lambda f: True,
    "Skip Optional Files": lambda f: not f.is_optional,
    "Main Game Only": lambda f: f.category in ("Main", "Setup"),
    "Language Packs Only": lambda f: f.category == "Language Pack",
    "Bonus Content Only": lambda f: f.category in ("Bonus", "Extras"),
    "Updates Only": lambda f: f.category == "Update",
}


@dataclass
class FileItem:
    """One downloadable file with full metadata."""

    url: str
    filename: str
    part_num: str
    size_str: str
    category: str
    language: str
    is_optional: bool
    is_selected: bool = True
    group_name: str = ""
    icon_char: str = ""
    badge_color: str = ""
    description: str = ""

    def __post_init__(self) -> None:
        if not self.group_name:
            self.group_name = self.category
        if not self.icon_char:
            self.icon_char = CATEGORY_ICONS.get(self.category, "\u25CB")
        if not self.badge_color:
            self.badge_color = BADGE_COLORS.get(self.category, ModernStyle.TEXT_SECONDARY)
        if not self.description:
            self.description = _build_description(self)


def _build_description(item: FileItem) -> str:
    parts: list[str] = []
    if item.is_optional:
        parts.append("Optional")
    else:
        parts.append("Required")
    if item.language:
        parts.append(item.language)
    if item.size_str:
        parts.append(item.size_str)
    return " \u00b7 ".join(parts) if parts else item.category


# ═══════════════════════════════════════════════════════════════════════════
# Smart detection
# ═══════════════════════════════════════════════════════════════════════════

_SETUP_RE = re.compile(
    r"setup|installer|autorun|\.exe$", re.IGNORECASE
)
_LANG_RE = re.compile(
    r"lang|language|selective|"
    r"english|russian|chinese|japanese|french|german|spanish|"
    r"portuguese|italian|korean|arabic|polish|turkish|czech|dutch|"
    r"hungarian|romanian|thai|vietnamese|brazilian|hindi",
    re.IGNORECASE,
)
_UPDATE_RE = re.compile(r"update|patch|hotfix|cumulative", re.IGNORECASE)
_BONUS_RE = re.compile(r"bonus|ost|soundtrack|wallpaper|artbook|manual|comic", re.IGNORECASE)
_CRACK_RE = re.compile(r"crack|fix|nosTEAM|skidrow|reloaded", re.IGNORECASE)
_DLC_RE = re.compile(r"\bdlc\b", re.IGNORECASE)
_REDIST_RE = re.compile(
    r"redistributable|vcredist|directx|\.net|openal|physx|ode|fmod",
    re.IGNORECASE,
)
_OPTIONAL_RE = re.compile(r"optional|bonus|extra|selective", re.IGNORECASE)
_LANG_CODE_RE = re.compile(
    r"\b(english|russian|chinese|japanese|french|german|spanish|"
    r"portuguese|italian|korean|arabic|polish|turkish|czech|dutch|"
    r"hungarian|romanian|thai|vietnamese|brazilian|hindi)\b",
    re.IGNORECASE,
)
_PART_RE = re.compile(r"part(\d+)", re.IGNORECASE)


def _detect_category(filename: str) -> tuple[str, bool]:
    low = filename.lower()
    # Language packs must be checked before setup — files like
    # "setup-fitgirl-selective-french.bin" are language files, not setup.
    if _LANG_RE.search(low) or _LANG_CODE_RE.search(low):
        return "Language Pack", True
    if _SETUP_RE.search(low):
        return "Setup", False
    if _OPTIONAL_RE.search(low):
        return "Optional", True
    if _CRACK_RE.search(low):
        return "Crack", True
    if _BONUS_RE.search(low):
        return "Bonus", True
    if _DLC_RE.search(low):
        return "DLC", True
    if _UPDATE_RE.search(low):
        return "Update", False
    if _REDIST_RE.search(low):
        return "Redistributable", False
    return "Main", False


def _detect_language(filename: str) -> str:
    m = _LANG_CODE_RE.search(filename)
    return m.group(1).title() if m else ""


# ═══════════════════════════════════════════════════════════════════════════
# Tree widget stylesheet
# ═══════════════════════════════════════════════════════════════════════════

_TREE_STYLE = f"""
QTreeWidget {{
    background-color: {ModernStyle.BG_PRIMARY};
    border: none;
    outline: none;
    font-size: 12px;
}}
QTreeWidget::item {{
    padding: 2px 0px;
    border: none;
    color: {ModernStyle.TEXT_PRIMARY};
}}
QTreeWidget::item:selected {{
    background-color: {ModernStyle.ACCENT}18;
    color: {ModernStyle.TEXT_PRIMARY};
}}
QTreeWidget::item:hover:!selected {{
    background-color: {ModernStyle.BG_HOVER};
}}
QTreeWidget::item:alternate {{
    background-color: {ModernStyle.BG_SECONDARY};
}}
QTreeWidget::branch {{
    background: transparent;
}}
QTreeWidget::branch:has-children:closed {{
    image: none;
    border-image: none;
}}
QTreeWidget::branch:has-children:open {{
    image: none;
    border-image: none;
}}
QTreeWidget::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 1.5px solid {ModernStyle.BORDER};
    background-color: {ModernStyle.BG_TERTIARY};
}}
QTreeWidget::indicator:checked {{
    background-color: {ModernStyle.ACCENT};
    border-color: {ModernStyle.ACCENT};
}}
QTreeWidget::indicator:hover {{
    border-color: {ModernStyle.BORDER_ACTIVE};
}}
QHeaderView::section {{
    background-color: {ModernStyle.BG_SECONDARY};
    color: {ModernStyle.TEXT_MUTED};
    border: none;
    border-bottom: 1px solid {ModernStyle.BORDER};
    padding: 6px 10px;
    font-size: 11px;
    font-weight: 600;
}}
"""


# ═══════════════════════════════════════════════════════════════════════════
# Main dialog
# ═══════════════════════════════════════════════════════════════════════════


class FileSelectionDialog(QDialog):
    """Full-size file-selection dialog with Windows Explorer behaviour.

    Features:
        * Flat and grouped views with collapsible categories
        * Click / Ctrl+Click / Shift+Click / Drag selection
        * Keyboard: Ctrl+A, Escape, Enter, Space, arrows, Home/End
        * Right-click context menu
        * Quick selection presets
        * Live search and multi-filter
        * Real-time selection summary
        * Smart file-type detection
    """

    def __init__(
        self,
        links: list[str],
        initial_state: dict[str, bool] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Select Files \u2014 FitFetch")
        self.setMinimumSize(1000, 650)
        self.resize(1200, 750)
        self.setModal(True)

        # data
        self._items: list[FileItem] = self._parse_links(links)

        # restore previous selection or use defaults
        if initial_state:
            for it in self._items:
                if it.url in initial_state:
                    it.is_selected = initial_state[it.url]
        self._initial_states: dict[str, bool] = {
            it.url: it.is_selected for it in self._items
        }

        # tree item -> FileItem index mapping via data role
        self._file_tree_items: list[QTreeWidgetItem] = []

        # selection state
        self._last_clicked_item: QTreeWidgetItem | None = None
        self._drag_active = False
        self._drag_initial_state = False
        self._updating_check = False

        # widgets (assigned during build)
        self._tree: QTreeWidget
        self._search_input: QLineEdit
        self._status_combo: QComboBox
        self._category_combo: QComboBox
        self._view_combo: QComboBox
        self._count_lbl: QLabel
        self._sel_count_lbl: QLabel
        self._total_size_lbl: QLabel
        self._req_count_lbl: QLabel
        self._opt_count_lbl: QLabel
        self._preview_lay: QVBoxLayout
        self._warning_lbl: QLabel
        self._fetch_btn: QPushButton

        self._build_ui()
        self._populate_tree()
        self._update_summary()

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_links(links: list[str]) -> list[FileItem]:
        items: list[FileItem] = []
        for url in links:
            filename = url.split("/")[-1].split("#")[-1]
            m = _PART_RE.search(filename)
            part_num = m.group(1) if m else ""
            cat, opt = _detect_category(filename)
            lang = _detect_language(filename)
            items.append(
                FileItem(
                    url=url,
                    filename=filename,
                    part_num=part_num,
                    size_str="",
                    category=cat,
                    language=lang,
                    is_optional=opt,
                    is_selected=not opt,
                )
            )
        return items

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.setStyleSheet(ModernStyle.dialog_style())
        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        content = QHBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)

        content.addWidget(self._build_left_panel(), 0)
        content.addWidget(self._build_center_panel(), 1)
        content.addWidget(self._build_right_panel(), 0)

        root.addLayout(content, 1)
        root.addWidget(self._build_bottom_bar(), 0)

    # ---- left panel ---------------------------------------------------

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(230)
        panel.setStyleSheet(
            f"background-color: {ModernStyle.BG_SECONDARY};"
            f"border-right: 1px solid {ModernStyle.BORDER};"
        )
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(12, 16, 12, 12)
        lay.setSpacing(8)

        title = QLabel("Filters")
        title.setStyleSheet(
            "font-size: 14px; font-weight: 700;"
            f"color: {ModernStyle.TEXT_PRIMARY};"
        )
        lay.addWidget(title)

        # search
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search files...")
        self._search_input.setFixedHeight(32)
        self._search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {ModernStyle.BG_TERTIARY};
                border: 1px solid {ModernStyle.BORDER};
                border-radius: {ModernStyle.RADIUS}px;
                padding: 6px 10px;
                color: {ModernStyle.TEXT_PRIMARY};
                font-size: 12px;
            }}
            QLineEdit:focus {{ border-color: {ModernStyle.BORDER_ACTIVE}; }}
        """)
        self._search_input.textChanged.connect(self._apply_filters)
        lay.addWidget(self._search_input)

        # status filter
        lbl = QLabel("Status")
        lbl.setStyleSheet(
            f"color: {ModernStyle.TEXT_MUTED}; font-size: 10px;"
            f"font-weight: 600; margin-top: 4px;"
        )
        lay.addWidget(lbl)
        self._status_combo = QComboBox()
        self._status_combo.setFixedHeight(30)
        self._status_combo.setStyleSheet(ModernStyle.combobox_style())
        self._status_combo.addItems([
            "All", "Required", "Optional", "Selected", "Unselected",
        ])
        self._status_combo.currentIndexChanged.connect(self._apply_filters)
        lay.addWidget(self._status_combo)

        # category filter
        lbl2 = QLabel("Category")
        lbl2.setStyleSheet(
            f"color: {ModernStyle.TEXT_MUTED}; font-size: 10px;"
            f"font-weight: 600; margin-top: 4px;"
        )
        lay.addWidget(lbl2)
        self._category_combo = QComboBox()
        self._category_combo.setFixedHeight(30)
        self._category_combo.setStyleSheet(ModernStyle.combobox_style())
        cats = ["All Categories"] + [
            c for c in CATEGORY_ORDER
            if any(it.category == c for it in self._items)
        ]
        self._category_combo.addItems(cats)
        self._category_combo.currentIndexChanged.connect(self._apply_filters)
        lay.addWidget(self._category_combo)

        lay.addWidget(self._sep())

        # view mode
        lbl3 = QLabel("View")
        lbl3.setStyleSheet(
            f"color: {ModernStyle.TEXT_MUTED}; font-size: 10px;"
            f"font-weight: 600; margin-top: 4px;"
        )
        lay.addWidget(lbl3)
        self._view_combo = QComboBox()
        self._view_combo.setFixedHeight(30)
        self._view_combo.setStyleSheet(ModernStyle.combobox_style())
        self._view_combo.addItems(["Flat List", "Grouped by Category"])
        self._view_combo.currentIndexChanged.connect(self._on_view_changed)
        lay.addWidget(self._view_combo)

        lay.addWidget(self._sep())

        # presets
        lbl4 = QLabel("Quick Select")
        lbl4.setStyleSheet(
            f"color: {ModernStyle.TEXT_MUTED}; font-size: 10px;"
            f"font-weight: 600; margin-top: 4px;"
        )
        lay.addWidget(lbl4)

        for name, _fn in PRESETS.items():
            btn = QPushButton(name)
            btn.setFixedHeight(30)
            btn.setStyleSheet(f"""
                QPushButton {{
                    text-align: left;
                    padding-left: 10px;
                    font-size: 11px;
                    background-color: {ModernStyle.BG_TERTIARY};
                    border: 1px solid {ModernStyle.BORDER};
                    border-radius: {ModernStyle.RADIUS}px;
                    color: {ModernStyle.TEXT_PRIMARY};
                }}
                QPushButton:hover {{
                    background-color: {ModernStyle.BG_HOVER};
                    border-color: {ModernStyle.BORDER_ACTIVE};
                }}
                QPushButton:pressed {{
                    background-color: {ModernStyle.BG_ACTIVE};
                }}
            """)
            btn.clicked.connect(
                lambda _, n=name: self._apply_preset(n)
            )
            lay.addWidget(btn)

        lay.addStretch()
        return panel

    # ---- center panel -------------------------------------------------

    def _build_center_panel(self) -> QWidget:
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # header
        hdr = QWidget()
        hdr.setStyleSheet(
            f"background-color: {ModernStyle.BG_SECONDARY};"
            f"border-bottom: 1px solid {ModernStyle.BORDER};"
        )
        hdr_l = QHBoxLayout(hdr)
        hdr_l.setContentsMargins(12, 8, 12, 8)
        self._count_lbl = QLabel(f"{len(self._items)} files")
        self._count_lbl.setStyleSheet(
            f"color: {ModernStyle.TEXT_MUTED}; font-size: 11px;"
        )
        hdr_l.addWidget(self._count_lbl)
        hdr_l.addStretch()
        lay.addWidget(hdr)

        # tree
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["#", "Filename"])
        self._tree.setRootIsDecorated(False)
        self._tree.setAlternatingRowColors(True)
        self._tree.setSelectionMode(
            QTreeWidget.SelectionMode.ExtendedSelection
        )
        self._tree.setUniformRowHeights(True)
        self._tree.setIndentation(24)
        self._tree.setAnimated(True)
        self._tree.setExpandsOnDoubleClick(True)
        self._tree.setStyleSheet(_TREE_STYLE)
        self._tree.header().setStretchLastSection(True)

        self._tree.itemChanged.connect(self._on_item_changed)
        self._tree.itemDoubleClicked.connect(self._on_double_click)
        self._tree.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self._tree.customContextMenuRequested.connect(
            self._on_context_menu
        )

        # viewport events for drag selection
        self._tree.viewport().installEventFilter(self)

        lay.addWidget(self._tree, 1)
        return panel

    # ---- right panel --------------------------------------------------

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(270)
        panel.setStyleSheet(
            f"background-color: {ModernStyle.BG_SECONDARY};"
            f"border-left: 1px solid {ModernStyle.BORDER};"
        )
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(16, 16, 16, 12)
        lay.setSpacing(8)

        lbl = QLabel("Selection Summary")
        lbl.setStyleSheet(
            "font-size: 14px; font-weight: 700;"
            f"color: {ModernStyle.TEXT_PRIMARY};"
        )
        lay.addWidget(lbl)

        self._sel_count_lbl = QLabel("0 / 0 files selected")
        self._sel_count_lbl.setStyleSheet(
            f"color: {ModernStyle.TEXT_SECONDARY}; font-size: 12px;"
        )
        lay.addWidget(self._sel_count_lbl)

        self._total_size_lbl = QLabel("Estimated size: \u2014")
        self._total_size_lbl.setStyleSheet(
            f"color: {ModernStyle.TEXT_SECONDARY}; font-size: 12px;"
        )
        lay.addWidget(self._total_size_lbl)

        self._req_count_lbl = QLabel("Required: 0 selected")
        self._req_count_lbl.setStyleSheet(
            f"color: {ModernStyle.SUCCESS}; font-size: 11px;"
        )
        lay.addWidget(self._req_count_lbl)

        self._opt_count_lbl = QLabel("Optional: 0 selected")
        self._opt_count_lbl.setStyleSheet(
            f"color: {ModernStyle.WARNING}; font-size: 11px;"
        )
        lay.addWidget(self._opt_count_lbl)

        lay.addWidget(self._sep())

        self._warning_lbl = QLabel("")
        self._warning_lbl.setWordWrap(True)
        self._warning_lbl.setStyleSheet(
            f"color: {ModernStyle.ERROR}; font-size: 11px;"
            f"background-color: {ModernStyle.ERROR}12;"
            f"border: 1px solid {ModernStyle.ERROR}33;"
            f"border-radius: {ModernStyle.RADIUS}px;"
            f"padding: 8px;"
        )
        self._warning_lbl.setVisible(False)
        lay.addWidget(self._warning_lbl)

        plbl = QLabel("Selected files:")
        plbl.setStyleSheet(
            f"color: {ModernStyle.TEXT_MUTED}; font-size: 10px;"
            f"font-weight: 600; margin-top: 4px;"
        )
        lay.addWidget(plbl)

        ps = QScrollArea()
        ps.setWidgetResizable(True)
        ps.setStyleSheet(
            f"background-color: {ModernStyle.BG_PRIMARY};"
            f"border: 1px solid {ModernStyle.BORDER};"
            f"border-radius: {ModernStyle.RADIUS}px;"
        )
        pw = QWidget()
        self._preview_lay = QVBoxLayout(pw)
        self._preview_lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._preview_lay.setSpacing(1)
        self._preview_lay.setContentsMargins(8, 6, 8, 6)
        ps.setWidget(pw)
        lay.addWidget(ps, 1)

        return panel

    # ---- bottom bar ---------------------------------------------------

    def _build_bottom_bar(self) -> QWidget:
        bar = QWidget()
        bar.setStyleSheet(
            f"background-color: {ModernStyle.BG_SECONDARY};"
            f"border-top: 1px solid {ModernStyle.BORDER};"
        )
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 10, 16, 10)
        lay.setSpacing(6)

        h = 32
        for text, slot in [
            ("Select All", self._select_all),
            ("Deselect All", self._deselect_all),
            ("Invert Selection", self._invert_selection),
            ("Reset", self._reset_selection),
        ]:
            b = QPushButton(text)
            b.setFixedHeight(h)
            b.clicked.connect(slot)
            lay.addWidget(b)

        lay.addStretch()

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setFixedHeight(h)
        self._cancel_btn.clicked.connect(self.reject)
        lay.addWidget(self._cancel_btn)

        self._fetch_btn = QPushButton("Fetch Selected Links")
        self._fetch_btn.setFixedHeight(h)
        self._fetch_btn.setProperty("primary", True)
        self._fetch_btn.setEnabled(False)
        self._fetch_btn.clicked.connect(self.accept)
        lay.addWidget(self._fetch_btn)

        return bar

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _sep() -> QWidget:
        w = QWidget()
        w.setFixedHeight(1)
        w.setStyleSheet(f"background-color: {ModernStyle.BORDER};")
        return w

    def _visible_file_items(self) -> list[FileItem]:
        """Return file items that pass the current filters."""
        query = self._search_input.text().lower()
        status = self._status_combo.currentText()
        cat = self._category_combo.currentText()
        result: list[FileItem] = []
        for it in self._items:
            if query and query not in it.filename.lower():
                continue
            if status == "Required" and it.is_optional:
                continue
            if status == "Optional" and not it.is_optional:
                continue
            if status == "Selected" and not it.is_selected:
                continue
            if status == "Unselected" and it.is_selected:
                continue
            if cat != "All Categories" and it.category != cat:
                continue
            result.append(it)
        return result

    # ------------------------------------------------------------------
    # Tree population
    # ------------------------------------------------------------------

    def _populate_tree(self) -> None:
        self._tree.blockSignals(True)
        self._tree.clear()
        self._file_tree_items.clear()

        is_grouped = self._view_combo.currentIndex() == 1
        visible = self._visible_file_items()

        if is_grouped:
            self._populate_grouped(visible)
        else:
            self._populate_flat(visible)

        self._tree.blockSignals(False)
        total = len(self._items)
        shown = len(visible)
        self._count_lbl.setText(
            f"{shown} files" if shown == total else f"{shown}/{total} files"
        )

    def _populate_flat(self, items: list[FileItem]) -> None:
        self._tree.setRootIsDecorated(False)
        sorted_items = sorted(items, key=lambda it: (
            0 if it.part_num.isdigit() else 1,
            int(it.part_num) if it.part_num.isdigit() else 0,
        ))
        text_col = QColor(ModernStyle.TEXT_PRIMARY)
        part_col = QColor(ModernStyle.ACCENT)
        vis_idx = 0
        for item in sorted_items:
            real_idx = self._items.index(item)
            twi = QTreeWidgetItem()
            part_text = f"#{item.part_num}" if item.part_num else ""
            twi.setData(0, Qt.ItemDataRole.DisplayRole, part_text)
            twi.setData(1, Qt.ItemDataRole.DisplayRole, item.filename)
            twi.setData(0, _FILE_ITEM_ROLE, real_idx)
            twi.setForeground(0, part_col)
            twi.setForeground(1, text_col)
            twi.setCheckState(0, Qt.CheckState.Checked if item.is_selected else Qt.CheckState.Unchecked)
            twi.setSizeHint(0, QSize(0, 32))
            if vis_idx % 2 == 1:
                twi.setBackground(0, QColor(ModernStyle.BG_SECONDARY))
                twi.setBackground(1, QColor(ModernStyle.BG_SECONDARY))
            self._tree.addTopLevelItem(twi)
            self._file_tree_items.append(twi)
            vis_idx += 1
        self._tree.setColumnWidth(0, 50)

    def _populate_grouped(self, items: list[FileItem]) -> None:
        self._tree.setRootIsDecorated(True)
        visible_set = set(id(it) for it in items)
        groups: dict[str, list[tuple[int, FileItem]]] = {}
        for idx, it in enumerate(self._items):
            if id(it) not in visible_set:
                continue
            groups.setdefault(it.group_name, []).append((idx, it))

        for gname in CATEGORY_ORDER:
            gitems = groups.get(gname, [])
            if not gitems:
                continue
            color = BADGE_COLORS.get(gname, ModernStyle.TEXT_SECONDARY)

            # sort within group by part number
            gitems.sort(key=lambda t: (
                0 if t[1].part_num.isdigit() else 1,
                int(t[1].part_num) if t[1].part_num.isdigit() else 0,
            ))

            hdr = QTreeWidgetItem()
            hdr.setData(0, Qt.ItemDataRole.DisplayRole, f"{gname}  ({len(gitems)})")
            font_h = self._tree.font()
            font_h.setBold(True)
            hdr.setFont(0, font_h)
            hdr.setBackground(0, QColor(ModernStyle.BG_TERTIARY))
            hdr.setBackground(1, QColor(ModernStyle.BG_TERTIARY))
            hdr.setForeground(0, QColor(color))
            hdr.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsAutoTristate)
            self._tree.addTopLevelItem(hdr)

            vis_idx = 0
            text_col = QColor(ModernStyle.TEXT_PRIMARY)
            part_col = QColor(ModernStyle.ACCENT)
            for real_idx, item in gitems:
                twi = QTreeWidgetItem(hdr)
                part_text = f"#{item.part_num}" if item.part_num else ""
                twi.setData(0, Qt.ItemDataRole.DisplayRole, part_text)
                twi.setData(1, Qt.ItemDataRole.DisplayRole, item.filename)
                twi.setData(0, _FILE_ITEM_ROLE, real_idx)
                twi.setForeground(0, part_col)
                twi.setForeground(1, text_col)
                twi.setCheckState(0, Qt.CheckState.Checked if item.is_selected else Qt.CheckState.Unchecked)
                twi.setSizeHint(0, QSize(0, 28))
                if vis_idx % 2 == 1:
                    twi.setBackground(0, QColor(ModernStyle.BG_SECONDARY))
                    twi.setBackground(1, QColor(ModernStyle.BG_SECONDARY))
                self._file_tree_items.append(twi)
                vis_idx += 1
            hdr.setExpanded(True)

    # ------------------------------------------------------------------
    # Item changed (checkbox toggle)
    # ------------------------------------------------------------------

    def _on_item_changed(self, twi: QTreeWidgetItem, _col: int) -> None:
        if self._updating_check:
            return
        item = self._get_file_item(twi)
        if item is None:
            return
        item.is_selected = twi.checkState(0) == Qt.CheckState.Checked
        # update parent group header state
        parent = twi.parent()
        if parent is not None:
            self._update_group_header(parent)
        self._update_summary()

    def _update_group_header(self, header: QTreeWidgetItem) -> None:
        total = header.childCount()
        if total == 0:
            return
        checked = sum(
            1 for i in range(total)
            if header.child(i).checkState(0) == Qt.CheckState.Checked
        )
        self._updating_check = True
        if checked == 0:
            header.setCheckState(0, Qt.CheckState.Unchecked)
        elif checked == total:
            header.setCheckState(0, Qt.CheckState.Checked)
        else:
            header.setCheckState(0, Qt.CheckState.PartiallyChecked)
        self._updating_check = False

    def _get_file_item(self, twi: QTreeWidgetItem) -> FileItem | None:
        idx = twi.data(0, _FILE_ITEM_ROLE)
        if idx is not None and 0 <= idx < len(self._items):
            return self._items[idx]
        return None

    def _set_item_checked(self, twi: QTreeWidgetItem, checked: bool) -> None:
        item = self._get_file_item(twi)
        if item is None:
            return
        item.is_selected = checked
        self._updating_check = True
        twi.setCheckState(0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        self._updating_check = False

    # ------------------------------------------------------------------
    # Keyboard
    # ------------------------------------------------------------------

    def _build_shortcuts(self) -> None:
        pass  # handled in keyPressEvent

    def keyPressEvent(self, event) -> None:
        k = event.key()
        mods = event.modifiers()
        ctrl = bool(mods & Qt.KeyboardModifier.ControlModifier)

        if k == Qt.Key.Key_Space:
            self._toggle_focused()
            return
        if k in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self._fetch_btn.isEnabled():
                self.accept()
            return
        if k == Qt.Key.Key_Escape:
            self.reject()
            return
        if ctrl and k == Qt.Key.Key_A:
            self._select_all_visible()
            return
        if k == Qt.Key.Key_Home:
            items = self._all_file_items()
            if items:
                self._tree.setCurrentItem(items[0])
            return
        if k == Qt.Key.Key_End:
            items = self._all_file_items()
            if items:
                self._tree.setCurrentItem(items[-1])
            return

        super().keyPressEvent(event)

    def _toggle_focused(self) -> None:
        cur = self._tree.currentItem()
        if cur is None:
            return
        item = self._get_file_item(cur)
        if item is None:
            # group header — toggle all children
            for i in range(cur.childCount()):
                child = cur.child(i)
                child_item = self._get_file_item(child)
                if child_item:
                    self._set_item_checked(child, not child_item.is_selected)
            self._update_summary()
            return
        self._set_item_checked(cur, not item.is_selected)
        self._update_summary()

    # ------------------------------------------------------------------
    # Mouse / drag selection
    # ------------------------------------------------------------------

    def eventFilter(self, obj, event) -> bool:
        if obj is self._tree.viewport():
            etype = event.type()

            if etype == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                item = self._tree.itemAt(event.pos())
                if item:
                    fi = self._get_file_item(item)
                    if fi is None:
                        # group header — toggle all children
                        any_unchecked = any(
                            c.checkState(0) == Qt.CheckState.Unchecked
                            for c in (item.child(i) for i in range(item.childCount()))
                        )
                        self._tree.blockSignals(True)
                        for i in range(item.childCount()):
                            child = item.child(i)
                            self._set_item_checked(child, any_unchecked)
                        self._tree.blockSignals(False)
                        self._update_summary()
                    else:
                        self._drag_active = True
                        self._drag_initial_state = fi.is_selected

            elif etype == QEvent.Type.MouseMove and self._drag_active:
                item = self._tree.itemAt(event.pos())
                if item:
                    fi = self._get_file_item(item)
                    if fi:
                        self._set_item_checked(item, not self._drag_initial_state)
                        self._update_summary()

            elif etype == QEvent.Type.MouseButtonRelease:
                self._drag_active = False

        return super().eventFilter(obj, event)

    # ------------------------------------------------------------------
    # Double-click
    # ------------------------------------------------------------------

    def _on_double_click(self, twi: QTreeWidgetItem, _col) -> None:
        item = self._get_file_item(twi)
        if item:
            self._set_item_checked(twi, not item.is_selected)
            self._update_summary()

    # ------------------------------------------------------------------
    # Context menu
    # ------------------------------------------------------------------

    def _on_context_menu(self, pos) -> None:
        item = self._tree.itemAt(pos)
        if item is None:
            return
        fi = self._get_file_item(item)
        if fi is None:
            return

        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {ModernStyle.BG_SECONDARY};
                border: 1px solid {ModernStyle.BORDER};
                border-radius: {ModernStyle.RADIUS}px;
                padding: 4px 0px;
            }}
            QMenu::item {{
                padding: 6px 24px 6px 16px;
                color: {ModernStyle.TEXT_PRIMARY};
            }}
            QMenu::item:selected {{
                background-color: {ModernStyle.BG_TERTIARY};
            }}
        """)

        menu.addAction("Select", lambda: self._set_item_checked(item, True))
        menu.addAction("Deselect", lambda: self._set_item_checked(item, False))
        menu.addSeparator()
        menu.addAction(
            "Select Similar Files",
            lambda: self._select_by_pattern(fi.filename),
        )
        menu.addAction(
            f"Select All in \"{fi.category}\"",
            lambda: self._select_by_category(fi.category),
        )
        menu.addSeparator()
        menu.addAction(
            "Copy Filename",
            lambda: QApplication.clipboard().setText(fi.filename),
        )

        menu.exec(QCursor.pos())

    # ------------------------------------------------------------------
    # Selection actions
    # ------------------------------------------------------------------

    def _select_all_visible(self) -> None:
        self._tree.blockSignals(True)
        for twi in self._all_file_items():
            self._set_item_checked(twi, True)
        self._tree.blockSignals(False)
        self._update_summary()

    def _select_all(self) -> None:
        self._select_all_visible()

    def _deselect_all(self) -> None:
        self._tree.blockSignals(True)
        for twi in self._all_file_items():
            self._set_item_checked(twi, False)
        self._tree.blockSignals(False)
        self._update_summary()

    def _invert_selection(self) -> None:
        self._tree.blockSignals(True)
        for twi in self._all_file_items():
            fi = self._get_file_item(twi)
            if fi:
                self._set_item_checked(twi, not fi.is_selected)
        self._tree.blockSignals(False)
        self._update_summary()

    def _reset_selection(self) -> None:
        self._tree.blockSignals(True)
        for twi in self._all_file_items():
            fi = self._get_file_item(twi)
            if fi:
                self._set_item_checked(twi, not fi.is_optional)
        self._tree.blockSignals(False)
        self._search_input.clear()
        self._status_combo.setCurrentIndex(0)
        self._category_combo.setCurrentIndex(0)
        self._update_summary()

    def _apply_preset(self, name: str) -> None:
        fn = PRESETS.get(name)
        if fn is None:
            return
        self._tree.blockSignals(True)
        for twi in self._all_file_items():
            fi = self._get_file_item(twi)
            if fi:
                self._set_item_checked(twi, fn(fi))
        self._tree.blockSignals(False)
        self._update_summary()

    def _select_by_pattern(self, pattern: str) -> None:
        base = re.sub(r"part\d+", "", pattern, flags=re.IGNORECASE).lower()
        self._tree.blockSignals(True)
        for twi in self._all_file_items():
            fi = self._get_file_item(twi)
            if fi and base and base in fi.filename.lower():
                self._set_item_checked(twi, True)
        self._tree.blockSignals(False)
        self._update_summary()

    def _select_by_category(self, category: str) -> None:
        self._tree.blockSignals(True)
        for twi in self._all_file_items():
            fi = self._get_file_item(twi)
            if fi and fi.category == category:
                self._set_item_checked(twi, True)
        self._tree.blockSignals(False)
        self._update_summary()

    # ------------------------------------------------------------------
    # Filters
    # ------------------------------------------------------------------

    def _apply_filters(self) -> None:
        self._populate_tree()

    def _on_view_changed(self, _idx: int) -> None:
        self._populate_tree()

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def _update_summary(self) -> None:
        total = len(self._items)
        sel = [it for it in self._items if it.is_selected]
        n = len(sel)
        req_sel = sum(1 for it in sel if not it.is_optional)
        opt_sel = sum(1 for it in sel if it.is_optional)
        req_total = sum(1 for it in self._items if not it.is_optional)

        self._sel_count_lbl.setText(f"{n} / {total} files selected")
        self._fetch_btn.setEnabled(n > 0)

        self._req_count_lbl.setText(f"Required: {req_sel} selected")
        self._opt_count_lbl.setText(f"Optional: {opt_sel} selected")

        self._total_size_lbl.setText("Estimated size: \u2014")

        # warning
        show_warn = req_total > 0 and req_sel == 0
        self._warning_lbl.setVisible(show_warn)
        if show_warn:
            self._warning_lbl.setText(
                "\u26a0 No required files selected. "
                "The download may be incomplete."
            )

        # preview
        while self._preview_lay.count():
            child = self._preview_lay.takeAt(0)
            w = child.widget()
            if w:
                w.deleteLater()

        for it in sel[:100]:
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(4)

            icon = QLabel(it.icon_char)
            icon.setFixedWidth(16)
            icon.setStyleSheet(
                f"color: {it.badge_color}; font-size: 11px;"
            )
            row.addWidget(icon)

            name = QLabel(it.filename)
            name.setStyleSheet(
                f"color: {ModernStyle.TEXT_SECONDARY}; font-size: 11px;"
            )
            row.addWidget(name, 1)

            container = QWidget()
            container.setLayout(row)
            self._preview_lay.addWidget(container)

        if n > 100:
            lbl = QLabel(f"  \u2026 and {n - 100} more")
            lbl.setStyleSheet(
                f"color: {ModernStyle.TEXT_MUTED}; font-size: 10px;"
                f"font-style: italic;"
            )
            self._preview_lay.addWidget(lbl)

        if not sel:
            lbl = QLabel("  No files selected")
            lbl.setStyleSheet(
                f"color: {ModernStyle.TEXT_MUTED}; font-size: 11px;"
            )
            self._preview_lay.addWidget(lbl)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _all_file_items(self) -> list[QTreeWidgetItem]:
        return list(self._file_tree_items)

    def get_selected_links(self) -> list[str]:
        """Return URLs for every ticked file."""
        return [it.url for it in self._items if it.is_selected]

    def get_selection_state(self) -> dict[str, bool]:
        """Return the full selection state (URL -> checked) for persistence."""
        return {it.url: it.is_selected for it in self._items}
