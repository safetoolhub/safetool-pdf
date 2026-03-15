# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Screen for managing PDF permissions, passwords, and restrictions.

Shows a professional table with per-file permission checkboxes, password
handling for encrypted files, and editable output names.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFontMetrics, QPainter
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from safetool_pdf_core.models import PdfPermissions, ProgressInfo, ToolName, ToolResult
from safetool_pdf_core.naming import output_path_for
from safetool_pdf_desktop.styles.design_system import DesignSystem
from safetool_pdf_desktop.styles.icons import icon_manager
from i18n import tr

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Permission metadata
# ---------------------------------------------------------------------------

# Each permission maps to a PdfPermissions field. Short UI labels are i18n keys
# that appear in column headers; descriptions are shown in the legend.
_PERMISSION_FIELDS: list[dict] = [
    {
        "field": "print_lowres",
        "header_key": "unlock_screen.perm_print_short",
        "desc_key": "unlock_screen.perm_print_desc",
        "icon": "printer",
        "color": DesignSystem.COLOR_PRIMARY,
    },
    {
        "field": "print_highres",
        "header_key": "unlock_screen.perm_print_hq_short",
        "desc_key": "unlock_screen.perm_print_hq_desc",
        "icon": "printer-check",
        "color": DesignSystem.COLOR_PRIMARY,
    },
    {
        "field": "modify_other",
        "header_key": "unlock_screen.perm_modify_short",
        "desc_key": "unlock_screen.perm_modify_desc",
        "icon": "file-edit",
        "color": DesignSystem.COLOR_WARNING,
    },
    {
        "field": "extract",
        "header_key": "unlock_screen.perm_extract_short",
        "desc_key": "unlock_screen.perm_extract_desc",
        "icon": "file-export",
        "color": DesignSystem.COLOR_INFO,
    },
    {
        "field": "modify_annotation",
        "header_key": "unlock_screen.perm_annotate_short",
        "desc_key": "unlock_screen.perm_annotate_desc",
        "icon": "comment-edit",
        "color": DesignSystem.COLOR_WARNING,
    },
    {
        "field": "fill_forms",
        "header_key": "unlock_screen.perm_forms_short",
        "desc_key": "unlock_screen.perm_forms_desc",
        "icon": "form-textbox",
        "color": DesignSystem.COLOR_WARNING,
    },
    {
        "field": "accessibility",
        "header_key": "unlock_screen.perm_access_short",
        "desc_key": "unlock_screen.perm_access_desc",
        "icon": "human",
        "color": DesignSystem.COLOR_SUCCESS,
    },
    {
        "field": "modify_assembly",
        "header_key": "unlock_screen.perm_assembly_short",
        "desc_key": "unlock_screen.perm_assembly_desc",
        "icon": "file-multiple",
        "color": DesignSystem.COLOR_DANGER,
    },
]


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


class ElidedLabel(QLabel):
    """A QLabel that automatically elides its text with '…' if it overflows."""

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
            self.text(), Qt.TextElideMode.ElideRight, self.width(),
        )
        painter.drawText(self.rect(), self.alignment(), elided)
        painter.end()


# ======================================================================
# UnlockScreen
# ======================================================================

class UnlockScreen(QWidget):
    """Screen for modifying PDF permissions and passwords.

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
        self._passwords: dict[int, str] = {}            # idx → password
        self._file_needs_password: dict[int, bool] = {}  # idx → needs pw
        self._file_unlocked: dict[int, bool] = {}        # idx → pw validated
        self._file_permissions: dict[int, PdfPermissions] = {}
        self._output_names: dict[int, str] = {}
        self._worker = None
        self._perm_checkboxes: dict[int, dict[str, QCheckBox]] = {}  # idx → {field → cb}
        self._password_widgets: dict[int, QWidget] = {}  # idx → pw input container
        self._remove_password_cbs: dict[int, QCheckBox] = {}  # idx → remove pw checkbox
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
        lay.setSpacing(16)

        # ── Top bar ──
        top = QHBoxLayout()
        self._back_btn = QPushButton(tr("strategy.back"))
        icon_manager.set_button_icon(self._back_btn, "arrow-left", size=16)
        self._back_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        self._back_btn.clicked.connect(self._on_back)
        top.addWidget(self._back_btn)
        top.addSpacing(16)

        icon_lbl = QLabel()
        icon_manager.set_label_icon(
            icon_lbl, "lock-open-variant",
            color=DesignSystem.COLOR_SUCCESS, size=24,
        )
        top.addWidget(icon_lbl)
        top.addSpacing(8)

        self._title_label = QLabel(tr("unlock_screen.title"))
        self._title_label.setStyleSheet(DesignSystem.get_strategy_header_text_style())
        top.addWidget(self._title_label)
        top.addStretch()

        self._file_info_label = QLabel()
        self._file_info_label.setStyleSheet(DesignSystem.get_strategy_info_text_style())
        top.addWidget(self._file_info_label)
        lay.addLayout(top)

        # ── Subtitle ──
        self._subtitle = QLabel(tr("unlock_screen.subtitle"))
        self._subtitle.setWordWrap(True)
        self._subtitle.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"color: {DesignSystem.COLOR_TEXT_SECONDARY};"
        )
        lay.addWidget(self._subtitle)

        # ── Permission legend ──
        self._legend_frame = QFrame()
        self._legend_frame.setStyleSheet(DesignSystem.get_strategy_legend_card_style())
        legend_lay = QVBoxLayout(self._legend_frame)
        legend_lay.setContentsMargins(16, 12, 16, 12)
        legend_lay.setSpacing(8)

        legend_title_row = QHBoxLayout()
        legend_title_row.setSpacing(8)
        legend_ic = QLabel()
        icon_manager.set_label_icon(legend_ic, "information-outline", color=DesignSystem.COLOR_PRIMARY, size=16)
        legend_title_row.addWidget(legend_ic)
        legend_title = QLabel(tr("unlock_screen.legend_title"))
        legend_title.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
            f"color: {DesignSystem.COLOR_TEXT};"
        )
        legend_title_row.addWidget(legend_title)
        legend_title_row.addStretch()
        legend_lay.addLayout(legend_title_row)

        # Grid of permission descriptions
        perm_grid = QGridLayout()
        perm_grid.setHorizontalSpacing(24)
        perm_grid.setVerticalSpacing(6)
        for i, pm in enumerate(_PERMISSION_FIELDS):
            row = i // 2
            col = i % 2

            item_w = QWidget()
            item_lay = QHBoxLayout(item_w)
            item_lay.setContentsMargins(0, 0, 0, 0)
            item_lay.setSpacing(6)

            # The number label is removed in favor of using just icons.

            ic = QLabel()
            icon_manager.set_label_icon(ic, pm["icon"], color=pm["color"], size=14)
            ic.setStyleSheet("border: none; background: transparent;")
            item_lay.addWidget(ic)

            abbr = QLabel(f"<b>{tr(pm['header_key'])}</b>")
            abbr.setStyleSheet(
                f"font-size: {DesignSystem.FONT_SIZE_XS}px;"
                f"color: {DesignSystem.COLOR_TEXT};"
                f"border: none; background: transparent;"
            )
            item_lay.addWidget(abbr)

            desc = QLabel(tr(pm['desc_key']))
            desc.setStyleSheet(
                f"font-size: {DesignSystem.FONT_SIZE_XS}px;"
                f"color: {DesignSystem.COLOR_TEXT_SECONDARY};"
                f"border: none; background: transparent;"
            )
            desc.setWordWrap(True)
            item_lay.addWidget(desc, 1)

            perm_grid.addWidget(item_w, row, col)

        legend_lay.addLayout(perm_grid)
        lay.addWidget(self._legend_frame)

        # ── Permissions table ──
        table_frame = QFrame()
        table_frame.setStyleSheet(DesignSystem.get_estimation_table_container_style())
        tf_lay = QVBoxLayout(table_frame)
        tf_lay.setContentsMargins(0, 0, 0, 0)
        self._table_container = QVBoxLayout()
        self._table_container.setSpacing(0)
        tf_lay.addLayout(self._table_container)
        lay.addWidget(table_frame)

        # ── New password section ──
        self._new_password_frame = QFrame()
        self._new_password_frame.setStyleSheet(DesignSystem.get_custom_panel_style())
        np_lay = QVBoxLayout(self._new_password_frame)
        np_lay.setContentsMargins(16, 12, 16, 12)
        np_lay.setSpacing(DesignSystem.SPACE_12)

        np_title_row = QHBoxLayout()
        np_ic = QLabel()
        icon_manager.set_label_icon(np_ic, "lock", color=DesignSystem.COLOR_PRIMARY, size=16)
        np_title_row.addWidget(np_ic)
        np_title_row.addSpacing(8)
        np_title = QLabel(tr("unlock_screen.new_password_title"))
        np_title.setStyleSheet(DesignSystem.get_custom_section_header_style())
        np_title_row.addWidget(np_title)
        np_title_row.addStretch()
        np_lay.addLayout(np_title_row)

        np_desc = QLabel(tr("unlock_screen.new_password_desc"))
        np_desc.setWordWrap(True)
        np_desc.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f"border: none; background: transparent;"
        )
        np_lay.addWidget(np_desc)

        pw_row = QHBoxLayout()
        pw_row.setSpacing(12)

        user_pw_container = QVBoxLayout()
        user_pw_label = QLabel(tr("unlock_screen.user_password_label"))
        user_pw_label.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_XS}px;"
            f"font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
            f"color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f"text-transform: uppercase;"
            f"border: none; background: transparent;"
        )
        user_pw_container.addWidget(user_pw_label)
        self._new_user_pw = QLineEdit()
        self._new_user_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self._new_user_pw.setPlaceholderText(tr("unlock_screen.user_password_placeholder"))
        self._new_user_pw.setStyleSheet(DesignSystem.get_line_edit_style())
        self._new_user_pw.setMinimumWidth(200)
        user_pw_container.addWidget(self._new_user_pw)
        pw_row.addLayout(user_pw_container)

        owner_pw_container = QVBoxLayout()
        owner_pw_label = QLabel(tr("unlock_screen.owner_password_label"))
        owner_pw_label.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_XS}px;"
            f"font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
            f"color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f"text-transform: uppercase;"
            f"border: none; background: transparent;"
        )
        owner_pw_container.addWidget(owner_pw_label)
        self._new_owner_pw = QLineEdit()
        self._new_owner_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self._new_owner_pw.setPlaceholderText(tr("unlock_screen.owner_password_placeholder"))
        self._new_owner_pw.setStyleSheet(DesignSystem.get_line_edit_style())
        self._new_owner_pw.setMinimumWidth(200)
        owner_pw_container.addWidget(self._new_owner_pw)
        pw_row.addLayout(owner_pw_container)

        pw_row.addStretch()
        np_lay.addLayout(pw_row)
        lay.addWidget(self._new_password_frame)

        # ── Execute button row ──
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._remove_all_btn = QPushButton(f"  {tr('unlock_screen.btn_remove_all')}")
        self._remove_all_btn.setMinimumHeight(44)
        self._remove_all_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        self._remove_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        icon_manager.set_button_icon(
            self._remove_all_btn, "unlock",
            color=DesignSystem.COLOR_TEXT, size=18,
        )
        self._remove_all_btn.clicked.connect(self._on_remove_all)
        btn_row.addWidget(self._remove_all_btn)
        btn_row.addSpacing(12)

        self._execute_btn = QPushButton(f"  {tr('unlock_screen.btn_apply')}")
        self._execute_btn.setMinimumHeight(44)
        self._execute_btn.setStyleSheet(DesignSystem.get_primary_button_style())
        self._execute_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        icon_manager.set_button_icon(
            self._execute_btn, "check-bold",
            color=DesignSystem.COLOR_PRIMARY_TEXT, size=18,
        )
        self._execute_btn.clicked.connect(self._on_execute)
        btn_row.addWidget(self._execute_btn)
        lay.addLayout(btn_row)

        # ── Progress (hidden by default) ──
        self._progress_container = QWidget()
        prog_layout = QVBoxLayout(self._progress_container)
        prog_layout.setContentsMargins(0, DesignSystem.SPACE_12, 0, 0)
        prog_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        prog_layout.setSpacing(12)

        prog_ic = QLabel()
        icon_manager.set_label_icon(
            prog_ic, "progress-clock", color=DesignSystem.COLOR_PRIMARY, size=48,
        )
        prog_layout.addWidget(prog_ic, 0, Qt.AlignmentFlag.AlignCenter)

        self._progress_label = QLabel(tr("simple_tool.progress_title"))
        self._progress_label.setStyleSheet(DesignSystem.get_strategy_header_text_style())
        prog_layout.addWidget(self._progress_label, 0, Qt.AlignmentFlag.AlignCenter)

        self._progress_status = QLabel("")
        self._progress_status.setStyleSheet(DesignSystem.get_strategy_info_text_style())
        prog_layout.addWidget(self._progress_status, 0, Qt.AlignmentFlag.AlignCenter)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setStyleSheet(DesignSystem.get_progressbar_style())
        self._progress_bar.setFixedWidth(400)
        prog_layout.addWidget(self._progress_bar, 0, Qt.AlignmentFlag.AlignCenter)

        self._cancel_btn = QPushButton(tr("strategy.cancel"))
        self._cancel_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        self._cancel_btn.clicked.connect(self._on_cancel)
        prog_layout.addWidget(self._cancel_btn, 0, Qt.AlignmentFlag.AlignCenter)

        self._progress_container.setVisible(False)
        lay.addWidget(self._progress_container)

        lay.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll)

    # ------------------------------------------------------------------
    # Table construction
    # ------------------------------------------------------------------

    def _rebuild_table(self) -> None:
        """Build the permissions table."""
        while self._table_container.count():
            item = self._table_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._perm_checkboxes.clear()
        self._password_widgets.clear()
        self._remove_password_cbs.clear()

        if not self._files:
            return

        # ── Header row ──
        header = QFrame()
        header.setStyleSheet(DesignSystem.get_file_table_header_style())
        hl = QHBoxLayout(header)
        hl.setContentsMargins(12, 6, 12, 6)
        hl.setSpacing(4)

        # File name column
        file_lbl = QLabel(tr("unlock_screen.col_file"))
        file_lbl.setStyleSheet(DesignSystem.get_table_header_cell_style())
        hl.addWidget(file_lbl, 3)

        # Password column (highlighted) moved to first place after file
        pw_header_w = QWidget()
        pw_header_w.setFixedWidth(50)
        pw_header_w.setStyleSheet(
            f"QWidget {{ background-color: {DesignSystem.COLOR_WARNING_BG}; "
            f"border-left: 2px solid {DesignSystem.COLOR_WARNING}; "
            f"border-right: 2px solid {DesignSystem.COLOR_WARNING}; }}"
        )
        pw_header_lay = QHBoxLayout(pw_header_w)
        pw_header_lay.setContentsMargins(0, 0, 0, 0)
        pw_lbl = QLabel()
        icon_manager.set_label_icon(pw_lbl, "lock", color=DesignSystem.COLOR_WARNING_TEXT, size=18)
        pw_lbl.setToolTip(tr("unlock_screen.col_password"))
        pw_header_lay.addWidget(pw_lbl, 0, Qt.AlignmentFlag.AlignCenter)
        hl.addWidget(pw_header_w)

        # Permission columns
        for col_idx, pm in enumerate(_PERMISSION_FIELDS):
            col_lbl = QLabel()
            icon_manager.set_label_icon(col_lbl, pm["icon"], color=pm["color"], size=16)
            col_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            col_lbl.setStyleSheet("border: none; background: transparent;")
            col_lbl.setFixedWidth(45)
            col_lbl.setToolTip(f"{tr(pm['header_key'])} — {tr(pm['desc_key'])}")
            hl.addWidget(col_lbl)

        # Output name column
        out_lbl = QLabel(tr("unlock_screen.col_output"))
        out_lbl.setStyleSheet(DesignSystem.get_table_header_cell_style())
        hl.addWidget(out_lbl, 2)

        self._table_container.addWidget(header)

        # ── "Select all" row ──
        select_row = QFrame()
        select_row.setStyleSheet(
            f"QFrame {{ background-color: {DesignSystem.COLOR_PRIMARY_LIGHT};"
            f"border-bottom: 1px solid {DesignSystem.COLOR_BORDER_LIGHT}; }}"
        )
        sr_lay = QHBoxLayout(select_row)
        sr_lay.setContentsMargins(12, 4, 12, 4)
        sr_lay.setSpacing(4)

        sa_label = QLabel(tr("unlock_screen.select_all"))
        sa_label.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_XS}px;"
            f"font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
            f"color: {DesignSystem.COLOR_PRIMARY};"
            f"background: transparent; border: none;"
        )
        sr_lay.addWidget(sa_label, 3)

        # Empty space for password column (highlighted column part)
        pw_spacer = QWidget()
        pw_spacer.setFixedWidth(50)
        pw_spacer.setStyleSheet(
            f"QWidget {{ background-color: {DesignSystem.COLOR_WARNING_BG}; "
            f"border-left: 2px solid {DesignSystem.COLOR_WARNING}; "
            f"border-right: 2px solid {DesignSystem.COLOR_WARNING}; }}"
        )
        sr_lay.addWidget(pw_spacer)

        self._select_all_cbs: dict[str, QCheckBox] = {}
        for pm in _PERMISSION_FIELDS:
            cb = QCheckBox()
            cb.setStyleSheet(DesignSystem.get_checkbox_style())
            cb.setChecked(True)
            cb.stateChanged.connect(
                lambda state, field=pm["field"]: self._on_select_all_changed(field, state),
            )
            # Center the checkbox
            cb_container = QWidget()
            cb_container.setFixedWidth(45)
            cb_container.setStyleSheet("QWidget { border: none; background: transparent; }")
            cb_lay = QHBoxLayout(cb_container)
            cb_lay.setContentsMargins(0, 0, 0, 0)
            cb_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cb_lay.addWidget(cb)
            sr_lay.addWidget(cb_container)
            self._select_all_cbs[pm["field"]] = cb

        sr_lay.addWidget(QWidget(), 2)  # output spacer

        self._table_container.addWidget(select_row)

        # ── Data rows ──
        for i, path in enumerate(self._files):
            row = self._build_file_row(i, path)
            self._table_container.addWidget(row)

        # ── Update select-all checkboxes to match actual file permissions ──
        self._sync_select_all_state()

    def _build_file_row(self, idx: int, path: Path) -> QFrame:
        """Build one row in the permissions table."""
        needs_pw = self._file_needs_password.get(idx, False)
        unlocked = self._file_unlocked.get(idx, True)

        row = QFrame()
        row.setStyleSheet(DesignSystem.get_file_table_row_style(idx % 2 == 0))
        rl = QHBoxLayout(row)
        rl.setContentsMargins(12, 4, 12, 4)
        rl.setSpacing(4)

        # ── File name with eye button ──
        name_w = QWidget()
        name_w.setStyleSheet("QWidget { border: none; background: transparent; }")
        name_lay = QHBoxLayout(name_w)
        name_lay.setContentsMargins(0, 0, 0, 0)
        name_lay.setSpacing(6)

        eye_btn = QToolButton()
        eye_btn.setToolTip(tr("simple_tool.open_file"))
        icon_manager.set_button_icon(eye_btn, "eye", color=DesignSystem.COLOR_PRIMARY, size=14)
        eye_btn.setStyleSheet(DesignSystem.get_icon_button_style())
        eye_btn.setFixedSize(24, 24)
        eye_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        eye_btn.clicked.connect(lambda _=False, p=path: self._open_pdf(p))
        name_lay.addWidget(eye_btn)

        name_lbl = ElidedLabel(path.name)
        name_lbl.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
            f"color: {DesignSystem.COLOR_TEXT};"
        )
        name_lbl.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        name_lbl.customContextMenuRequested.connect(
            lambda pos, i=idx, w=name_lbl: self._show_context_menu(w, pos, i),
        )
        name_lay.addWidget(name_lbl, 1)
        rl.addWidget(name_w, 3)

        # If file needs password and is not yet unlocked → show password input
        if needs_pw and not unlocked:
            pw_container = QWidget()
            pw_container.setStyleSheet("QWidget { border: none; background: transparent; }")
            pw_lay = QHBoxLayout(pw_container)
            pw_lay.setContentsMargins(0, 0, 0, 0)
            pw_lay.setSpacing(6)

            lock_ic = QLabel()
            icon_manager.set_label_icon(lock_ic, "lock", color=DesignSystem.COLOR_DANGER, size=14)
            pw_lay.addWidget(lock_ic)

            pw_input = QLineEdit()
            pw_input.setEchoMode(QLineEdit.EchoMode.Password)
            pw_input.setPlaceholderText(tr("unlock_screen.enter_password"))
            pw_input.setStyleSheet(DesignSystem.get_line_edit_style())
            pw_input.setMinimumWidth(150)
            pw_lay.addWidget(pw_input, 1)

            validate_btn = QPushButton(tr("unlock_screen.btn_validate"))
            validate_btn.setStyleSheet(DesignSystem.get_primary_button_style())
            validate_btn.setFixedHeight(32)
            validate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            validate_btn.clicked.connect(
                lambda _=False, i=idx, inp=pw_input: self._on_validate_password(i, inp.text()),
            )
            pw_lay.addWidget(validate_btn)

            # Enter key also validates
            pw_input.returnPressed.connect(
                lambda i=idx, inp=pw_input: self._on_validate_password(i, inp.text()),
            )

            self._password_widgets[idx] = pw_container
            rl.addWidget(pw_container, 8 + 2)  # spans permission cols + pw col + output col
            return row

        # ── Password checkbox (remove password) ──
        # Highlighted and placed before permissions
        pw_cb = QCheckBox()
        pw_cb.setStyleSheet(DesignSystem.get_checkbox_style())
        pw_cb.setChecked(needs_pw)  # checked = has password; user can uncheck to remove
        pw_cb.setToolTip(tr("unlock_screen.password_tooltip"))

        pw_cb_container = QWidget()
        pw_cb_container.setFixedWidth(50)
        pw_cb_container.setStyleSheet(
            f"QWidget {{ background-color: {DesignSystem.COLOR_WARNING_BG}; "
            f"border-left: 2px solid {DesignSystem.COLOR_WARNING}; "
            f"border-right: 2px solid {DesignSystem.COLOR_WARNING}; }}"
        )
        pw_cb_lay = QHBoxLayout(pw_cb_container)
        pw_cb_lay.setContentsMargins(0, 0, 0, 0)
        pw_cb_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pw_cb_lay.addWidget(pw_cb)
        rl.addWidget(pw_cb_container)
        self._remove_password_cbs[idx] = pw_cb

        # ── Permission checkboxes ──
        perms = self._file_permissions.get(idx, PdfPermissions())
        self._perm_checkboxes[idx] = {}

        for pm in _PERMISSION_FIELDS:
            cb = QCheckBox()
            cb.setStyleSheet(DesignSystem.get_checkbox_style())
            cb.setChecked(getattr(perms, pm["field"], True))

            cb_container = QWidget()
            cb_container.setFixedWidth(45)
            cb_container.setStyleSheet("QWidget { border: none; background: transparent; }")
            cb_lay = QHBoxLayout(cb_container)
            cb_lay.setContentsMargins(0, 0, 0, 0)
            cb_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cb_lay.addWidget(cb)
            rl.addWidget(cb_container)
            self._perm_checkboxes[idx][pm["field"]] = cb

        # ── Output name ──
        output_name = self._get_output_name(idx)
        out_edit = QLineEdit(output_name)
        out_edit.setStyleSheet(
            DesignSystem.get_line_edit_style().replace(
                DesignSystem.COLOR_TEXT, DesignSystem.COLOR_PRIMARY,
            )
        )
        out_edit.textChanged.connect(lambda text, i=idx: self._on_output_name_changed(i, text))
        rl.addWidget(out_edit, 2)

        return row

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_output_name(self, idx: int) -> str:
        if idx in self._output_names:
            return self._output_names[idx]
        return output_path_for(self._files[idx]).name

    def _on_output_name_changed(self, idx: int, text: str) -> None:
        text = text.strip()
        if text:
            self._output_names[idx] = text

    def _on_select_all_changed(self, field: str, state: int) -> None:
        """Toggle a permission for all files at once."""
        checked = state == Qt.CheckState.Checked.value
        for idx, cbs in self._perm_checkboxes.items():
            if field in cbs:
                cbs[field].setChecked(checked)

    def _sync_select_all_state(self) -> None:
        """Set each select-all checkbox to match whether ALL files have that permission."""
        for pm in _PERMISSION_FIELDS:
            field = pm["field"]
            if field not in self._select_all_cbs:
                continue
            # Check if ALL file checkboxes for this field are checked
            all_checked = all(
                cbs[field].isChecked()
                for cbs in self._perm_checkboxes.values()
                if field in cbs
            )
            cb = self._select_all_cbs[field]
            cb.blockSignals(True)
            cb.setChecked(all_checked)
            cb.blockSignals(False)

    def _on_validate_password(self, idx: int, password: str) -> None:
        """Validate password for an encrypted file."""
        import pikepdf

        path = self._files[idx]
        try:
            pdf = pikepdf.open(str(path), password=password)
            pdf.close()
        except pikepdf.PasswordError:
            # Show inline error
            if idx in self._password_widgets:
                # Flash the row red briefly
                _logger.warning("Wrong password for %s", path.name)
            return
        except Exception as exc:
            _logger.error("Error validating password: %s", exc)
            return

        # Password is correct
        self._passwords[idx] = password
        self._file_unlocked[idx] = True

        # Read permissions now that we can open the file
        from safetool_pdf_core.tools.unlock import read_stored_permissions
        self._file_permissions[idx] = read_stored_permissions(path, password)

        self._rebuild_table()

    def _collect_permissions(self, idx: int) -> PdfPermissions:
        """Read current checkbox states into a PdfPermissions."""
        cbs = self._perm_checkboxes.get(idx, {})
        return PdfPermissions(
            print_lowres=cbs.get("print_lowres", QCheckBox()).isChecked() if "print_lowres" in cbs else True,
            print_highres=cbs.get("print_highres", QCheckBox()).isChecked() if "print_highres" in cbs else True,
            modify_other=cbs.get("modify_other", QCheckBox()).isChecked() if "modify_other" in cbs else True,
            extract=cbs.get("extract", QCheckBox()).isChecked() if "extract" in cbs else True,
            modify_annotation=cbs.get("modify_annotation", QCheckBox()).isChecked() if "modify_annotation" in cbs else True,
            fill_forms=cbs.get("fill_forms", QCheckBox()).isChecked() if "fill_forms" in cbs else True,
            accessibility=cbs.get("accessibility", QCheckBox()).isChecked() if "accessibility" in cbs else True,
            modify_assembly=cbs.get("modify_assembly", QCheckBox()).isChecked() if "modify_assembly" in cbs else True,
        )

    def _show_context_menu(self, widget: QWidget, pos, file_idx: int) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(DesignSystem.get_context_menu_style())
        path = self._files[file_idx]

        view_action = menu.addAction(tr("simple_tool.view_details"))
        view_action.triggered.connect(lambda: self._show_details(path))

        menu.exec(widget.mapToGlobal(pos))

    def _show_details(self, path: Path) -> None:
        from safetool_pdf_core.analyzer import analyze
        from safetool_pdf_desktop.dialogs.details_dialog import DetailsDialog

        try:
            analysis = analyze(path)
        except Exception:
            return
        dlg = DetailsDialog(analysis, parent=self)
        dlg.exec()

    def _open_pdf(self, path: Path) -> None:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_files(self, files: list[Path]) -> None:
        """Set up the screen with the given files."""
        if self._worker is not None and self._worker.isRunning():
            self._worker.request_cancel()
            self._worker.wait(2000)

        self._files = list(files)
        self._passwords.clear()
        self._file_needs_password.clear()
        self._file_unlocked.clear()
        self._file_permissions.clear()
        self._output_names.clear()
        self._worker = None

        # File info
        total_size = sum(f.stat().st_size for f in files if f.is_file())
        self._file_info_label.setText(
            tr("simple_tool.files_info", count=len(files), size=_format_size(total_size)),
        )

        # Reset UI
        self._execute_btn.setVisible(True)
        self._remove_all_btn.setVisible(True)
        self._progress_container.setVisible(False)
        self._new_user_pw.clear()
        self._new_owner_pw.clear()

        # Analyze each file for encryption status and permissions
        self._analyze_files()
        self._rebuild_table()

    def _analyze_files(self) -> None:
        """Detect encryption and read permissions from each file."""
        import pikepdf
        from safetool_pdf_core.tools.unlock import read_stored_permissions

        for idx, path in enumerate(self._files):
            try:
                pdf = pikepdf.open(str(path))
                pdf.close()
                # File opened without password
                self._file_needs_password[idx] = False
                self._file_unlocked[idx] = True
                self._file_permissions[idx] = read_stored_permissions(path)
            except pikepdf.PasswordError:
                # Needs password
                self._file_needs_password[idx] = True
                self._file_unlocked[idx] = False
                self._file_permissions[idx] = PdfPermissions()
            except Exception:
                self._file_needs_password[idx] = False
                self._file_unlocked[idx] = True
                self._file_permissions[idx] = PdfPermissions()

    # ------------------------------------------------------------------
    # Slots — execute
    # ------------------------------------------------------------------

    def _on_back(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            self._worker.request_cancel()
            self._worker.wait(2000)
        self.go_back.emit()

    def _on_remove_all(self) -> None:
        """Remove all encryption and restrictions from files."""
        processable = [
            (idx, path) for idx, path in enumerate(self._files)
            if self._file_unlocked.get(idx, True)
        ]
        if not processable:
            return

        self._execute_btn.setVisible(False)
        self._remove_all_btn.setVisible(False)
        self._progress_container.setVisible(True)
        self._progress_bar.setValue(0)
        self._progress_status.setText("")

        from safetool_pdf_desktop.workers.unlock_worker import UnlockWorker

        files = [path for _, path in processable]
        passwords_list = {i: self._passwords.get(orig_idx, "") for i, (orig_idx, _) in enumerate(processable)}

        # Use the first available password (they could differ per file but
        # we pass the most common case — single password)
        password = next((self._passwords.get(idx, "") for idx in range(len(self._files)) if self._passwords.get(idx)), "")

        self._worker = UnlockWorker(
            files,
            password=password,
            remove_encryption=True,
            parent=self,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_execute(self) -> None:
        """Apply the configured permissions to all unlocked files."""
        processable = [
            (idx, path) for idx, path in enumerate(self._files)
            if self._file_unlocked.get(idx, True)
        ]
        if not processable:
            return

        self._execute_btn.setVisible(False)
        self._remove_all_btn.setVisible(False)
        self._progress_container.setVisible(True)
        self._progress_bar.setValue(0)
        self._progress_status.setText("")

        # Collect permissions from checkboxes  
        # Since the worker processes all files with the same permissions,
        # we use the first file's checkboxes as reference.
        # If files have different settings, we process them individually.
        from safetool_pdf_desktop.workers.unlock_worker import UnlockWorker

        files = [path for _, path in processable]
        # Use first file's permissions as the batch permissions
        first_idx = processable[0][0]
        perms = self._collect_permissions(first_idx)

        password = next(
            (self._passwords.get(idx, "") for idx in range(len(self._files)) if self._passwords.get(idx)),
            "",
        )

        new_user_pw = self._new_user_pw.text().strip()
        new_owner_pw = self._new_owner_pw.text().strip()

        # Check if all permissions are True and no new password → effectively remove encryption
        all_true = all(getattr(perms, pm["field"]) for pm in _PERMISSION_FIELDS)
        has_pw_cb = any(
            self._remove_password_cbs.get(idx, QCheckBox()).isChecked()
            for idx, _ in processable
        )
        remove_enc = all_true and not new_user_pw and not new_owner_pw and not has_pw_cb

        self._worker = UnlockWorker(
            files,
            password=password,
            new_permissions=perms if not remove_enc else None,
            new_user_password=new_user_pw,
            new_owner_password=new_owner_pw,
            remove_encryption=remove_enc,
            parent=self,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_cancel(self) -> None:
        if self._worker is not None:
            self._worker.request_cancel()

    @Slot(ProgressInfo)
    def _on_progress(self, info: ProgressInfo) -> None:
        self._progress_bar.setValue(int(info.percent))
        self._progress_status.setText(info.message)

    @Slot(list)
    def _on_finished(self, results: list[ToolResult]) -> None:
        self._worker = None
        # Rename output files to match custom names
        for idx, result in enumerate(results):
            if not result.success or not result.output_path:
                continue
            custom_name = self._output_names.get(idx)
            if custom_name and result.output_path.name != custom_name:
                new_path = result.output_path.parent / custom_name
                try:
                    result.output_path.rename(new_path)
                    result.output_path = new_path
                except OSError:
                    _logger.warning("Failed to rename %s to %s", result.output_path, new_path)
        self.tool_complete.emit(ToolName.UNLOCK, self._files, results)

    @Slot(str)
    def _on_error(self, msg: str) -> None:
        self._worker = None
        self._execute_btn.setVisible(True)
        self._remove_all_btn.setVisible(True)
        self._progress_container.setVisible(False)
        self._progress_status.setText(msg)
