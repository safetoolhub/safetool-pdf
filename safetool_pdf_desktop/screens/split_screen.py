# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Screen for the Split PDF tool.

Shows a mode selector (6 modes), output suffix input, a live preview table,
and a progress area.  Screen index 5 in the main window stack.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFontMetrics, QPainter
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from safetool_pdf_core.models import ProgressInfo, SplitMode, ToolName, ToolResult
from safetool_pdf_desktop.styles.design_system import DesignSystem
from safetool_pdf_desktop.styles.icons import icon_manager
from i18n import tr

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


class ElidedLabel(QLabel):
    """QLabel that elides its text with '…' when it overflows."""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setMinimumWidth(1)
        self._original_text = text

    def setText(self, text: str) -> None:  # noqa: N802
        self._original_text = text
        super().setText(text)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        metrics = QFontMetrics(self.font())
        elided = metrics.elidedText(
            self._original_text, Qt.TextElideMode.ElideRight, self.width(),
        )
        painter.drawText(self.rect(), self.alignment(), elided)
        painter.end()


class ModeCard(QFrame):
    """Clickable card representing a split mode."""

    clicked = Signal(int)

    def __init__(self, mode_id: int, title: str, icon_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.mode_id = mode_id
        self.icon_name = icon_name
        self._checked = False
        self.setObjectName("ModeCard")

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(44)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(8)

        self.icon_lbl = QLabel()
        icon_manager.set_label_icon(self.icon_lbl, self.icon_name, color=DesignSystem.COLOR_TEXT_SECONDARY, size=20)
        lay.addWidget(self.icon_lbl)

        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};"
            f"color: {DesignSystem.COLOR_TEXT};"
            f"border: none; background: transparent;"
        )
        lay.addWidget(self.title_lbl)
        lay.addStretch()

        self._update_style()

    def setChecked(self, checked: bool) -> None:  # noqa: N802
        if self._checked != checked:
            self._checked = checked
            self._update_style()

    def isChecked(self) -> bool:  # noqa: N802
        return self._checked

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.mode_id)
            super().mousePressEvent(event)

    def _update_style(self) -> None:
        if self._checked:
            self.setStyleSheet(f"""
                QFrame#ModeCard {{
                    background-color: {DesignSystem.COLOR_PRIMARY_SUBTLE};
                    border: 2px solid {DesignSystem.COLOR_PRIMARY};
                    border-radius: {DesignSystem.RADIUS_MD}px;
                }}
            """)
            icon_manager.set_label_icon(self.icon_lbl, self.icon_name, color=DesignSystem.COLOR_PRIMARY, size=20)
            self.title_lbl.setStyleSheet(
                f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
                f"font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
                f"color: {DesignSystem.COLOR_PRIMARY};"
                f"border: none; background: transparent;"
            )
        else:
            self.setStyleSheet(f"""
                QFrame#ModeCard {{
                    background-color: {DesignSystem.COLOR_SURFACE};
                    border: 1px solid {DesignSystem.COLOR_BORDER};
                    border-radius: {DesignSystem.RADIUS_MD}px;
                }}
                QFrame#ModeCard:hover {{
                    border-color: {DesignSystem.COLOR_BORDER};
                    background-color: {DesignSystem.COLOR_BACKGROUND};
                }}
            """)
            icon_manager.set_label_icon(self.icon_lbl, self.icon_name, color=DesignSystem.COLOR_TEXT_SECONDARY, size=20)
            self.title_lbl.setStyleSheet(
                f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
                f"font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};"
                f"color: {DesignSystem.COLOR_TEXT};"
                f"border: none; background: transparent;"
            )


# ---------------------------------------------------------------------------
# Mapping mode enum → stack page index
# ---------------------------------------------------------------------------

_MODE_TO_INDEX: dict[SplitMode, int] = {
    SplitMode.EVERY_PAGE:    0,
    SplitMode.ODD_EVEN:      1,
    SplitMode.EVERY_N_PAGES: 2,
    SplitMode.BY_RANGE:      3,
    SplitMode.BY_BOOKMARKS:  4,
    SplitMode.BY_SIZE:       5,
}

_INDEX_TO_MODE: dict[int, SplitMode] = {v: k for k, v in _MODE_TO_INDEX.items()}

# ---------------------------------------------------------------------------
# SplitScreen
# ---------------------------------------------------------------------------

class SplitScreen(QWidget):
    """Screen for splitting PDF files.

    Signals
    -------
    go_back : user clicked back.
    tool_complete(ToolName, list[Path], list[ToolResult]) : processing done.
    """

    go_back = Signal()
    tool_complete = Signal(object, list, list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._files: list[Path] = []
        self._page_counts: dict[int, int] = {}   # file index → page count
        self._file_sizes: dict[int, int] = {}    # file index → bytes
        self._bookmark_counts: dict[int, int] = {}  # file index → top-level bookmark count
        self._worker = None
        self._analysis_done: bool = False
        self._active_mode_id: int = _MODE_TO_INDEX[SplitMode.EVERY_PAGE]
        self._mode_cards: dict[int, ModeCard] = {}
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(DesignSystem.get_scroll_area_style())

        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(24, 16, 24, 24)
        lay.setSpacing(DesignSystem.SPACE_16)

        # ── Top bar ──
        top = QHBoxLayout()
        top.setSpacing(DesignSystem.SPACE_8)

        self._back_btn = QPushButton(tr("strategy.back"))
        icon_manager.set_button_icon(self._back_btn, "arrow-left", size=16)
        self._back_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        self._back_btn.clicked.connect(self._on_back)
        top.addWidget(self._back_btn)
        top.addSpacing(DesignSystem.SPACE_16)

        icon_lbl = QLabel()
        icon_manager.set_label_icon(
            icon_lbl, "scissors",
            color=DesignSystem.COLOR_PRIMARY, size=24,
        )
        top.addWidget(icon_lbl)
        top.addSpacing(DesignSystem.SPACE_8)

        self._title_label = QLabel(tr("split_screen.title"))
        self._title_label.setStyleSheet(DesignSystem.get_strategy_header_text_style())
        top.addWidget(self._title_label)
        top.addStretch()

        self._file_info_label = QLabel()
        self._file_info_label.setStyleSheet(DesignSystem.get_strategy_info_text_style())
        top.addWidget(self._file_info_label)
        lay.addLayout(top)

        # ── Subtitle ──
        subtitle = QLabel(tr("split_screen.subtitle"))
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"color: {DesignSystem.COLOR_TEXT_SECONDARY};"
        )
        lay.addWidget(subtitle)

        # ── Mode selector panel ──
        mode_frame = QFrame()
        mode_frame.setStyleSheet(DesignSystem.get_custom_panel_style())
        mode_lay = QVBoxLayout(mode_frame)
        mode_lay.setContentsMargins(12, 12, 12, 12)
        mode_lay.setSpacing(DesignSystem.SPACE_12)

        mode_header_row = QHBoxLayout()
        mode_ic = QLabel()
        icon_manager.set_label_icon(mode_ic, "tune", color=DesignSystem.COLOR_PRIMARY, size=18)
        mode_header_row.addWidget(mode_ic)
        mode_header_row.addSpacing(8)
        mode_title = QLabel(tr("split_screen.mode_label"))
        mode_title.setStyleSheet(DesignSystem.get_custom_section_header_style())
        mode_header_row.addWidget(mode_title)
        mode_header_row.addStretch()
        mode_lay.addLayout(mode_header_row)

        grid_layout = QGridLayout()
        grid_layout.setSpacing(DesignSystem.SPACE_8)

        _mode_keys: list[tuple[SplitMode, str, str]] = [
            (SplitMode.EVERY_PAGE,    "split_screen.mode_every_page", "file-document-multiple"),
            (SplitMode.ODD_EVEN,      "split_screen.mode_odd_even", "format-list-numbered"),
            (SplitMode.EVERY_N_PAGES, "split_screen.mode_every_n", "numeric"),
            (SplitMode.BY_RANGE,      "split_screen.mode_by_range", "arrow-expand-horizontal"),
            (SplitMode.BY_BOOKMARKS,  "split_screen.mode_by_bookmarks", "bookmark-multiple"),
            (SplitMode.BY_SIZE,       "split_screen.mode_by_size", "weight"),
        ]

        row, col = 0, 0
        for mode_val, key, icon_name in _mode_keys:
            m_id = _MODE_TO_INDEX[mode_val]
            card = ModeCard(m_id, tr(key), icon_name)
            card.clicked.connect(self._on_mode_clicked)
            self._mode_cards[m_id] = card
            grid_layout.addWidget(card, row, col)
            col += 1
            if col > 2:
                col = 0
                row += 1

        self._mode_cards[self._active_mode_id].setChecked(True)
        mode_lay.addLayout(grid_layout)

        # ── Dynamic sub-options (QStackedWidget) ──
        self._options_stack = QStackedWidget()
        self._options_stack.setContentsMargins(0, 0, 0, 0)
        self._options_stack.setMaximumHeight(66) # strict limit to prevent taking up space
        self._options_stack.setStyleSheet("border: none; background: transparent;")

        # Page 0 — EVERY_PAGE (info only)
        self._options_stack.addWidget(self._make_info_page("split_screen.mode_every_page_desc"))

        # Page 1 — ODD_EVEN (info only)
        self._options_stack.addWidget(self._make_info_page("split_screen.mode_odd_even_desc"))

        # Page 2 — EVERY_N_PAGES
        n_page = QWidget()
        n_lay = QHBoxLayout(n_page)
        n_lay.setContentsMargins(0, 0, 0, 0)
        n_lay.setSpacing(DesignSystem.SPACE_8)
        n_lbl = QLabel(tr("split_screen.every_n_label"))
        n_lbl.setStyleSheet(f"font-size: {DesignSystem.FONT_SIZE_SM}px; color: {DesignSystem.COLOR_TEXT}; font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM}; border: none; background: transparent;")
        n_lay.addWidget(n_lbl)
        self._n_spinbox = QSpinBox()
        self._n_spinbox.setMinimum(2)
        self._n_spinbox.setMaximum(9999)
        self._n_spinbox.setValue(2)
        self._n_spinbox.setMinimumWidth(80)
        self._n_spinbox.setStyleSheet(DesignSystem.get_spinbox_style())
        self._n_spinbox.valueChanged.connect(self._refresh_preview)
        n_lay.addWidget(self._n_spinbox)
        n_lay.addStretch()
        self._options_stack.addWidget(n_page)

        # Page 3 — BY_RANGE
        range_page = QWidget()
        range_lay = QHBoxLayout(range_page)
        range_lay.setContentsMargins(0, 0, 0, 0)
        range_lay.setSpacing(DesignSystem.SPACE_8)
        range_lbl = QLabel(tr("split_screen.range_label"))
        range_lbl.setStyleSheet(f"font-size: {DesignSystem.FONT_SIZE_SM}px; color: {DesignSystem.COLOR_TEXT}; font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM}; border: none; background: transparent;")
        range_lay.addWidget(range_lbl)
        self._range_edit = QLineEdit()
        self._range_edit.setPlaceholderText(tr("split_screen.range_placeholder"))
        self._range_edit.setMinimumWidth(150)
        self._range_edit.setStyleSheet(DesignSystem.get_line_edit_style())
        self._range_edit.textChanged.connect(self._refresh_preview)
        range_lay.addWidget(self._range_edit)
        range_hint = QLabel(tr("split_screen.range_hint"))
        range_hint.setStyleSheet(f"font-size: {DesignSystem.FONT_SIZE_SM}px; color: {DesignSystem.COLOR_TEXT_SECONDARY}; border: none; background: transparent;")
        range_lay.addWidget(range_hint)
        range_lay.addStretch()
        self._options_stack.addWidget(range_page)

        # Page 4 — BY_BOOKMARKS
        bm_page = QWidget()
        bm_lay = QHBoxLayout(bm_page)
        bm_lay.setContentsMargins(0, 0, 0, 0)
        self._bookmarks_info_label = QLabel(tr("split_screen.mode_by_bookmarks_desc"))
        self._bookmarks_info_label.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px; color: {DesignSystem.COLOR_TEXT_SECONDARY}; border: none; background: transparent;"
        )
        bm_lay.addWidget(self._bookmarks_info_label)
        self._options_stack.addWidget(bm_page)

        # Page 5 — BY_SIZE
        size_page = QWidget()
        size_lay = QHBoxLayout(size_page)
        size_lay.setContentsMargins(0, 0, 0, 0)
        size_lay.setSpacing(DesignSystem.SPACE_8)
        size_lbl = QLabel(tr("split_screen.size_label"))
        size_lbl.setStyleSheet(f"font-size: {DesignSystem.FONT_SIZE_SM}px; color: {DesignSystem.COLOR_TEXT}; font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM}; border: none; background: transparent;")
        size_lay.addWidget(size_lbl)
        self._size_spinbox = QDoubleSpinBox()
        self._size_spinbox.setMinimum(0.1)
        self._size_spinbox.setMaximum(9999.0)
        self._size_spinbox.setValue(1.0)
        self._size_spinbox.setDecimals(1)
        self._size_spinbox.setSuffix(" MB")
        self._size_spinbox.setMinimumWidth(100)
        self._size_spinbox.setStyleSheet(DesignSystem.get_spinbox_style())
        self._size_spinbox.valueChanged.connect(self._refresh_preview)
        size_lay.addWidget(self._size_spinbox)
        size_note = QLabel(tr("split_screen.size_note"))
        size_note.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px; color: {DesignSystem.COLOR_TEXT_SECONDARY}; font-style: italic; border: none; background: transparent;"
        )
        size_lay.addWidget(size_note)
        size_lay.addStretch()
        self._options_stack.addWidget(size_page)

        mode_lay.addWidget(self._options_stack)
        lay.addWidget(mode_frame)

        # ── Output settings panel ──
        out_frame = QFrame()
        out_frame.setStyleSheet(DesignSystem.get_custom_panel_style())
        out_lay = QVBoxLayout(out_frame)
        out_lay.setContentsMargins(12, 8, 12, 8)
        out_lay.setSpacing(DesignSystem.SPACE_8)

        out_header_row = QHBoxLayout()
        out_ic = QLabel()
        icon_manager.set_label_icon(out_ic, "file-document", color=DesignSystem.COLOR_PRIMARY, size=18)
        out_header_row.addWidget(out_ic)
        out_header_row.addSpacing(4)
        out_title = QLabel(tr("split_screen.output_label"))
        out_title.setStyleSheet(DesignSystem.get_custom_section_header_style())
        out_header_row.addWidget(out_title)
        
        out_header_row.addSpacing(16)
        
        suffix_lbl = QLabel(tr("split_screen.suffix_label"))
        suffix_lbl.setStyleSheet(f"font-size: {DesignSystem.FONT_SIZE_SM}px; color: {DesignSystem.COLOR_TEXT}; font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM}; border: none; background: transparent;")
        out_header_row.addWidget(suffix_lbl)
        self._suffix_edit = QLineEdit()
        self._suffix_edit.setText(tr("split_screen.suffix_default"))
        self._suffix_edit.setMinimumWidth(150)
        self._suffix_edit.setMaximumWidth(250)
        self._suffix_edit.setStyleSheet(DesignSystem.get_line_edit_style())
        self._suffix_edit.textChanged.connect(self._refresh_preview)
        out_header_row.addWidget(self._suffix_edit)
        out_header_row.addStretch()
        out_lay.addLayout(out_header_row)

        warn_row = QHBoxLayout()
        warn_row.setSpacing(DesignSystem.SPACE_8)
        warn_ic = QLabel()
        icon_manager.set_label_icon(warn_ic, "information", color=DesignSystem.COLOR_WARNING_TEXT, size=16)
        warn_row.addWidget(warn_ic, 0, Qt.AlignmentFlag.AlignTop)
        warn_lbl = QLabel(tr("split_screen.same_folder_warning"))
        warn_lbl.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"color: {DesignSystem.COLOR_WARNING_TEXT};"
            f"border: none; background: transparent;"
        )
        warn_row.addWidget(warn_lbl, 1, Qt.AlignmentFlag.AlignTop)
        
        warn_frame = QFrame()
        warn_frame.setStyleSheet(DesignSystem.get_warning_alert_style())
        warn_frame_lay = QVBoxLayout(warn_frame)
        warn_frame_lay.setContentsMargins(10, 6, 10, 6)
        warn_frame_lay.addLayout(warn_row)
        out_lay.addWidget(warn_frame)

        lay.addWidget(out_frame)

        # ── Preview table ──
        table_frame = QFrame()
        table_frame.setStyleSheet(DesignSystem.get_estimation_table_container_style())
        tf_lay = QVBoxLayout(table_frame)
        tf_lay.setContentsMargins(0, 0, 0, 0)
        tf_lay.setSpacing(0)

        # Header row
        header_row = QFrame()
        header_row.setStyleSheet(DesignSystem.get_file_table_header_style())
        hr_lay = QHBoxLayout(header_row)
        hr_lay.setContentsMargins(16, 12, 16, 12)
        hr_lay.setSpacing(DesignSystem.SPACE_12)
        for key, stretch in [
            ("split_screen.col_file", 3),
            ("split_screen.col_pages", 1),
            ("split_screen.col_chunks", 1),
        ]:
            lbl = QLabel(tr(key))
            lbl.setStyleSheet(DesignSystem.get_table_header_cell_style())
            hr_lay.addWidget(lbl, stretch)
        tf_lay.addWidget(header_row)

        self._preview_rows_container = QVBoxLayout()
        self._preview_rows_container.setSpacing(0)
        self._preview_rows_container.setContentsMargins(0, 0, 0, 0)
        tf_lay.addLayout(self._preview_rows_container)
        lay.addWidget(table_frame)

        # ── Execute button row ──
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._execute_btn = QPushButton(f"  {tr('split_screen.btn_split')}")
        self._execute_btn.setMinimumHeight(48)
        self._execute_btn.setMinimumWidth(220)
        self._execute_btn.setStyleSheet(DesignSystem.get_primary_button_style())
        self._execute_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        icon_manager.set_button_icon(
            self._execute_btn, "scissors",
            color=DesignSystem.COLOR_PRIMARY_TEXT, size=20,
        )
        self._execute_btn.clicked.connect(self._on_execute)
        btn_row.addWidget(self._execute_btn)
        lay.addLayout(btn_row)

        # ── Progress area (hidden by default) ──
        self._progress_container = QWidget()
        prog_lay = QVBoxLayout(self._progress_container)
        prog_lay.setContentsMargins(0, DesignSystem.SPACE_12, 0, 0)
        prog_lay.setSpacing(DesignSystem.SPACE_8)

        self._progress_label = QLabel(tr("split_screen.progress_title"))
        self._progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._progress_label.setStyleSheet(DesignSystem.get_strategy_header_text_style())
        prog_lay.addWidget(self._progress_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setStyleSheet(DesignSystem.get_progressbar_style())
        prog_lay.addWidget(self._progress_bar)

        self._progress_status = QLabel()
        self._progress_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._progress_status.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"color: {DesignSystem.COLOR_TEXT_SECONDARY};"
        )
        prog_lay.addWidget(self._progress_status)

        self._cancel_btn = QPushButton(f"  {tr('strategy.cancel')}")
        self._cancel_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        icon_manager.set_button_icon(self._cancel_btn, "close-circle", color=DesignSystem.COLOR_TEXT, size=16)
        self._cancel_btn.clicked.connect(self._on_cancel)
        cancel_row = QHBoxLayout()
        cancel_row.addStretch()
        cancel_row.addWidget(self._cancel_btn)
        cancel_row.addStretch()
        prog_lay.addLayout(cancel_row)

        self._progress_container.setVisible(False)
        lay.addWidget(self._progress_container)

        lay.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll)

    def _make_info_page(self, key: str) -> QWidget:
        """Create a simple info-text-only options page."""
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(DesignSystem.SPACE_8)
        
        lbl = QLabel(tr(key))
        lbl.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f"border: none; background: transparent;"
        )
        lay.addWidget(lbl)
        lay.addStretch()
        return w

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_files(self, files: list[Path]) -> None:
        """Configure this screen with *files* and run lightweight analysis."""
        # Cancel any running worker
        if self._worker is not None and self._worker.isRunning():
            self._worker.request_cancel()
            self._worker.wait(3000)
            self._worker = None

        self._files = list(files)
        self._page_counts.clear()
        self._file_sizes.clear()
        self._bookmark_counts.clear()
        self._analysis_done = False

        # Update file info label
        total_size = sum(f.stat().st_size for f in files if f.is_file())
        self._file_info_label.setText(
            tr("simple_tool.files_info", count=len(files), size=_format_size(total_size))
        )

        # Lightweight analysis (page count + bookmarks) — synchronous, fast
        self._run_analysis()

    # ------------------------------------------------------------------
    # Analysis (lightweight: page count + bookmarks only)
    # ------------------------------------------------------------------

    def _run_analysis(self) -> None:
        """Read page counts and bookmark counts synchronously (fast fitz calls)."""
        import fitz

        for i, path in enumerate(self._files):
            try:
                doc = fitz.open(str(path))
                page_count = doc.page_count
                toc = doc.get_toc(simple=True)
                top_level = [e for e in toc if e[0] == 1]
                doc.close()
                size = path.stat().st_size if path.is_file() else 0
                self._page_counts[i] = page_count
                self._file_sizes[i] = size
                self._bookmark_counts[i] = len(top_level)
            except Exception:
                self._page_counts[i] = 0
                self._file_sizes[i] = 0
                self._bookmark_counts[i] = 0

        self._analysis_done = True
        self._execute_btn.setEnabled(True)
        self._refresh_preview()

    # ------------------------------------------------------------------
    # Preview table
    # ------------------------------------------------------------------

    def _current_mode(self) -> SplitMode:
        return _INDEX_TO_MODE.get(self._active_mode_id, SplitMode.EVERY_PAGE)

    def _current_options(self) -> dict:
        mode = self._current_mode()
        if mode == SplitMode.EVERY_N_PAGES:
            return {"n": self._n_spinbox.value()}
        if mode == SplitMode.BY_RANGE:
            return {"ranges": self._range_edit.text()}
        if mode == SplitMode.BY_BOOKMARKS:
            return {}
        if mode == SplitMode.BY_SIZE:
            return {"target_mb": self._size_spinbox.value()}
        return {}

    def _refresh_preview(self) -> None:
        """Rebuild preview rows from current mode/options/page counts."""
        from safetool_pdf_core.tools.split import estimate_chunk_count

        # Clear old rows
        while self._preview_rows_container.count():
            item = self._preview_rows_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._files:
            return

        mode = self._current_mode()
        options = self._current_options()

        # For BY_BOOKMARKS, inject bookmark count per file
        for i, path in enumerate(self._files):
            pages = self._page_counts.get(i, 0)
            size = self._file_sizes.get(i, 0)

            per_file_options = dict(options)
            if mode == SplitMode.BY_BOOKMARKS:
                per_file_options["bookmark_count"] = self._bookmark_counts.get(i, 0)

            chunks = estimate_chunk_count(pages, size, mode, per_file_options)

            row_w = QFrame()
            row_w.setObjectName("previewRow")
            row_w.setStyleSheet(DesignSystem.get_file_table_row_style(i % 2 == 0))
            row_lay = QHBoxLayout(row_w)
            row_lay.setContentsMargins(16, 12, 16, 12)
            row_lay.setSpacing(DesignSystem.SPACE_12)

            name_lbl = ElidedLabel(path.name)
            name_lbl.setStyleSheet(DesignSystem.get_table_row_text_style())
            row_lay.addWidget(name_lbl, 3)

            pages_lbl = QLabel(str(pages) if pages > 0 else "—")
            pages_lbl.setStyleSheet(
                f"font-size: {DesignSystem.FONT_SIZE_SM}px; color: {DesignSystem.COLOR_TEXT_SECONDARY}; "
                f"border: none; background: transparent;"
            )
            row_lay.addWidget(pages_lbl, 1)

            if chunks > 0:
                chunks_text = tr("split_screen.chunks_estimated", count=chunks)
                chunks_color = DesignSystem.COLOR_PRIMARY
                font_weight = DesignSystem.FONT_WEIGHT_BOLD
            else:
                chunks_text = "—"
                chunks_color = DesignSystem.COLOR_TEXT_SECONDARY
                font_weight = DesignSystem.FONT_WEIGHT_MEDIUM
            chunks_lbl = QLabel(chunks_text)
            chunks_lbl.setStyleSheet(
                f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
                f"color: {chunks_color};"
                f"font-weight: {font_weight};"
                f"border: none; background: transparent;"
            )
            row_lay.addWidget(chunks_lbl, 1)

            self._preview_rows_container.addWidget(row_w)

    # ------------------------------------------------------------------
    # Slots — mode / option changes
    # ------------------------------------------------------------------

    @Slot(int)
    def _on_mode_clicked(self, mode_id: int) -> None:
        for mid, card in self._mode_cards.items():
            card.setChecked(mid == mode_id)

        self._active_mode_id = mode_id
        self._options_stack.setCurrentIndex(mode_id)
        # Update bookmarks label if needed
        if _INDEX_TO_MODE.get(mode_id) == SplitMode.BY_BOOKMARKS:
            total_bm = sum(self._bookmark_counts.get(i, 0) for i in range(len(self._files)))
            if total_bm == 0 and self._analysis_done:
                self._bookmarks_info_label.setText(tr("split_screen.no_bookmarks_warning"))
                self._bookmarks_info_label.setStyleSheet(
                    f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
                    f"color: {DesignSystem.COLOR_DANGER};"
                    f"border: none; background: transparent;"
                )
            else:
                self._bookmarks_info_label.setText(tr("split_screen.mode_by_bookmarks_desc"))
                self._bookmarks_info_label.setStyleSheet(
                    f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
                    f"color: {DesignSystem.COLOR_TEXT_SECONDARY};"
                    f"border: none; background: transparent;"
                )
        self._refresh_preview()

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    @Slot()
    def _on_execute(self) -> None:
        if not self._files:
            return

        from safetool_pdf_desktop.workers.split_worker import SplitWorker

        mode = self._current_mode()
        options = self._current_options()
        suffix = self._suffix_edit.text().strip() or tr("split_screen.suffix_default")

        self._worker = SplitWorker(
            files=self._files,
            mode=mode,
            options=options,
            suffix=suffix,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)

        self._execute_btn.setVisible(False)
        self._back_btn.setEnabled(False)
        self._progress_bar.setValue(0)
        self._progress_status.setText("")
        self._progress_container.setVisible(True)
        self._worker.start()

    @Slot(ProgressInfo)
    def _on_progress(self, info: ProgressInfo) -> None:
        self._progress_bar.setValue(int(info.percent))
        self._progress_status.setText(info.message)

    @Slot(list)
    def _on_finished(self, results: list[ToolResult]) -> None:
        self._progress_container.setVisible(False)
        self._execute_btn.setVisible(True)
        self._back_btn.setEnabled(True)
        self._worker = None
        self.tool_complete.emit(ToolName.SPLIT, self._files, results)

    @Slot(str)
    def _on_error(self, msg: str) -> None:
        from PySide6.QtWidgets import QMessageBox
        self._progress_container.setVisible(False)
        self._execute_btn.setVisible(True)
        self._back_btn.setEnabled(True)
        self._worker = None
        QMessageBox.critical(self, tr("split_screen.title"), msg)

    @Slot()
    def _on_cancel(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            self._worker.request_cancel()

    @Slot()
    def _on_back(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            self._worker.request_cancel()
            self._worker.wait(3000)
            self._worker = None
        self.go_back.emit()
