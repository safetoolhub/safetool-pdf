# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Screen 3: Final results after optimization."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from safetool_pdf_core.models import OptimizeResult, PresetName, ToolName, ToolResult
from safetool_pdf_desktop.styles.design_system import DesignSystem
from safetool_pdf_desktop.styles.icons import icon_manager
from i18n import tr


def _format_size(size_bytes: int) -> str:
    """Format bytes to human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


_PRESET_LABEL_KEYS: dict[PresetName | None, str] = {
    PresetName.LOSSLESS: "presets.lossless.label",
    PresetName.MODERATE: "presets.moderate.label",
    PresetName.AGGRESSIVE: "presets.aggressive.label",
    PresetName.CUSTOM: "presets.custom.label",
}


def _preset_label(preset: PresetName | None) -> str:
    key = _PRESET_LABEL_KEYS.get(preset)
    return tr(key) if key else "—"


class ResultsScreen(QWidget):
    """Screen 3 — Optimization results.

    Displays:
    - Success/warning header
    - Summary line (total savings)
    - Results table: file path, original name/size, new name/size, compression %
    - Action buttons: Open Folder, Optimise More Files

    Signals:
        go_back() — user wants to return to Screen 1
        open_file_requested(Path) — open a file
        open_folder_requested(Path) — open containing folder
    """

    go_back = Signal()
    use_another_tool = Signal(list)  # list[Path] — files to reuse
    open_file_requested = Signal(Path)
    open_folder_requested = Signal(Path)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._files: list[Path] = []
        self._results: list[OptimizeResult] = []
        self._tool_results: list[ToolResult] = []
        self._mode: str = "optimize"  # "optimize" or "tool"
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(DesignSystem.get_scroll_area_style())

        content = QWidget()
        self._content_layout = QVBoxLayout(content)
        self._content_layout.setSpacing(DesignSystem.SPACE_16)
        self._content_layout.setContentsMargins(
            DesignSystem.SPACE_16, DesignSystem.SPACE_12,
            DesignSystem.SPACE_16, DesignSystem.SPACE_12,
        )

        # Header title
        self._title_label = QLabel(tr("results.title"))
        self._title_label.setStyleSheet(DesignSystem.get_results_header_style(is_warning=False))
        self._content_layout.addWidget(self._title_label)

        # Summary line
        self._summary_label = QLabel("")
        self._summary_label.setStyleSheet(DesignSystem.get_results_summary_style())
        self._summary_label.setWordWrap(True)
        self._content_layout.addWidget(self._summary_label)

        # Results table container
        self._table_container = QVBoxLayout()
        self._table_container.setSpacing(0)
        self._content_layout.addLayout(self._table_container)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, DesignSystem.SPACE_12, 0, 0)
        btn_row.setSpacing(DesignSystem.SPACE_12)

        # Start Over — prominent, left-aligned
        start_over_btn = QPushButton(tr("results.start_over"))
        icon_manager.set_button_icon(start_over_btn, "restart", size=18)
        start_over_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        start_over_btn.setMinimumWidth(160)
        start_over_btn.clicked.connect(self.go_back.emit)
        btn_row.addWidget(start_over_btn)

        # Use another tool on the same files
        another_tool_btn = QPushButton(tr("results.use_another_tool"))
        icon_manager.set_button_icon(another_tool_btn, "tools", size=18)
        another_tool_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        another_tool_btn.setMinimumWidth(180)
        another_tool_btn.clicked.connect(lambda: self.use_another_tool.emit(self._files))
        btn_row.addWidget(another_tool_btn)

        btn_row.addStretch()

        # Export results to text
        export_btn = QPushButton(tr("results.export_report"))
        icon_manager.set_button_icon(export_btn, "file-export", size=16)
        export_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        export_btn.clicked.connect(self._on_export_report)
        btn_row.addWidget(export_btn)

        # Open Folder
        self._open_folder_btn = QPushButton(tr("results.open_folder"))
        icon_manager.set_button_icon(self._open_folder_btn, "folder-open", size=16)
        self._open_folder_btn.setStyleSheet(DesignSystem.get_primary_button_style())
        self._open_folder_btn.clicked.connect(self._on_open_folder)
        btn_row.addWidget(self._open_folder_btn)

        self._content_layout.addLayout(btn_row)
        self._content_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_file_cell(
        self,
        text: str,
        path: Path | None,
        color: str,
        tooltip: str,
        min_width: int = 150,
    ) -> tuple[QWidget, QLabel]:
        """Build a file cell with label and optional eye icon to open the PDF."""
        cell = QWidget()
        cell.setStyleSheet("background: transparent; border: none;")
        cell_layout = QHBoxLayout(cell)
        cell_layout.setContentsMargins(0, 0, 0, 0)
        cell_layout.setSpacing(DesignSystem.SPACE_4)

        if path is not None:
            eye_btn = QToolButton()
            eye_btn.setToolTip(tooltip)
            icon_manager.set_button_icon(
                eye_btn, "eye", color=DesignSystem.COLOR_PRIMARY, size=16,
            )
            eye_btn.setStyleSheet(DesignSystem.get_icon_button_style())
            eye_btn.setFixedSize(24, 24)
            eye_btn.clicked.connect(
                lambda _=False, p=path: self.open_file_requested.emit(p)
            )
            cell_layout.addWidget(eye_btn, 0)

        lbl = QLabel(text)
        style = DesignSystem.get_table_row_text_style()
        if color != DesignSystem.COLOR_TEXT:
            style = style.replace(DesignSystem.COLOR_TEXT, color)
        lbl.setStyleSheet(style)
        lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        cell_layout.addWidget(lbl, 1)

        cell.setMinimumWidth(min_width)
        return cell, lbl

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_results(self, files: list[Path], results: list[OptimizeResult]) -> None:
        """Populate the results screen with optimization results."""
        self._mode = "optimize"
        self._files = files
        self._results = results
        self._tool_results = []

        ok = [r for r in results if not r.skipped]
        n_ok = len(ok)
        n_skip = len(results) - n_ok

        # Header
        if n_skip == 0:
            self._title_label.setText(tr("results.title"))
            self._title_label.setStyleSheet(DesignSystem.get_results_header_style(is_warning=False))
        else:
            self._title_label.setText(tr("results.title_skipped", count=n_skip))
            self._title_label.setStyleSheet(DesignSystem.get_results_header_style(is_warning=True))

        # Summary
        if ok:
            total_orig = sum(r.original_size for r in ok)
            total_opt = sum(r.optimized_size for r in ok)
            saved = total_orig - total_opt
            avg_pct = (saved / total_orig * 100) if total_orig else 0
            self._summary_label.setText(
                tr("results.summary_ok",
                   size=_format_size(saved), pct=f"{avg_pct:.1f}",
                   ok=n_ok, total=len(results))
            )
        else:
            self._summary_label.setText(tr("results.summary_none"))

        self._rebuild_table()

    def set_tool_results(
        self, tool: ToolName, files: list[Path], results: list[ToolResult],
    ) -> None:
        """Populate the results screen with non-optimization tool results."""
        self._mode = "tool"
        self._files = files
        self._results = []
        self._tool_results = results

        successes = sum(1 for r in results if r.success)
        total = len(results)

        # Header
        if successes == total:
            self._title_label.setText(tr("tool_results.title_success"))
            self._title_label.setStyleSheet(DesignSystem.get_results_header_style(is_warning=False))
        elif successes > 0:
            self._title_label.setText(tr("tool_results.title_partial"))
            self._title_label.setStyleSheet(DesignSystem.get_results_header_style(is_warning=True))
        else:
            self._title_label.setText(tr("tool_results.title_failure"))
            self._title_label.setStyleSheet(DesignSystem.get_results_header_style(is_warning=True))

        # Summary
        if tool == ToolName.MERGE and results and results[0].success:
            size_str = _format_size(results[0].output_size)
            self._summary_label.setText(
                tr("tool_results.summary_merge", count=len(files), size=size_str)
            )
        else:
            self._summary_label.setText(
                tr("tool_results.summary_batch", success=successes, total=total)
            )

        self._rebuild_tool_table()

    # ------------------------------------------------------------------
    # Table building
    # ------------------------------------------------------------------

    def _rebuild_table(self) -> None:
        """Build the results table."""
        # Clear existing
        while self._table_container.count():
            item = self._table_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

        if not self._results:
            return

        # Header row
        header = QFrame()
        header.setObjectName("resultsTableHeader")
        header.setStyleSheet(DesignSystem.get_file_table_header_style())
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(
            DesignSystem.SPACE_12, DesignSystem.SPACE_4,
            DesignSystem.SPACE_12, DesignSystem.SPACE_4,
        )
        h_layout.setSpacing(DesignSystem.SPACE_8)

        for label_text, stretch, min_w, align in [
            (tr("results.header_file_path"), 2, 120, Qt.AlignmentFlag.AlignLeft),
            (tr("results.header_original"), 2, 150, Qt.AlignmentFlag.AlignLeft),
            (tr("results.header_optimised"), 2, 150, Qt.AlignmentFlag.AlignLeft),
            (tr("results.header_strategy"), 1, 80, Qt.AlignmentFlag.AlignCenter),
            (tr("results.header_compression"), 1, 90, Qt.AlignmentFlag.AlignCenter),
        ]:
            lbl = QLabel(label_text)
            lbl.setStyleSheet(DesignSystem.get_table_header_cell_style(is_active=False))
            lbl.setAlignment(align | Qt.AlignmentFlag.AlignVCenter)
            lbl.setMinimumWidth(min_w)
            h_layout.addWidget(lbl, stretch)

        self._table_container.addWidget(header)

        # Data rows
        for i, result in enumerate(self._results):
            row = self._build_result_row(i, result)
            self._table_container.addWidget(row)

        # Summary row
        summary = self._build_summary_row()
        if summary:
            self._table_container.addWidget(summary)

    def _build_result_row(self, index: int, result: OptimizeResult) -> QFrame:
        """Build one row of the results table."""
        even = index % 2 == 0

        row = QFrame()
        if not result.skipped:
            row.setStyleSheet(DesignSystem.get_file_table_row_optimized_style(even))
        else:
            row.setStyleSheet(DesignSystem.get_file_table_row_style(even))

        h = QHBoxLayout(row)
        h.setContentsMargins(
            DesignSystem.SPACE_12, DesignSystem.SPACE_2,
            DesignSystem.SPACE_12, DesignSystem.SPACE_2,
        )
        h.setSpacing(DesignSystem.SPACE_8)

        base = (
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"border: none; background: transparent;"
        )
        mono = (
            f"font-family: {DesignSystem.FONT_FAMILY_MONO};"
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"border: none; background: transparent;"
        )

        # File path (directory)
        dir_text = str(result.input_path.parent)
        if len(dir_text) > 40:
            dir_text = "…" + dir_text[-37:]
        dir_lbl = QLabel(dir_text)
        dir_lbl.setStyleSheet(DesignSystem.get_table_row_text_style().replace(DesignSystem.COLOR_TEXT, DesignSystem.COLOR_TEXT_SECONDARY))
        dir_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        dir_lbl.setMinimumWidth(120)
        h.addWidget(dir_lbl, 2)

        # Original name + size + eye icon
        orig_text = f"{result.input_path.name} — {_format_size(result.original_size)}"
        orig_cell, orig_lbl = self._build_file_cell(
            orig_text, result.input_path,
            DesignSystem.COLOR_TEXT,
            tr("results.open_original_tooltip"),
        )
        orig_cell.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        orig_cell.customContextMenuRequested.connect(
            lambda pos, r=result, w=orig_cell: self._show_original_file_context_menu(w, pos, r)
        )
        h.addWidget(orig_cell, 2)

        # Optimized name + size + eye icon
        if not result.skipped:
            new_text = f"{result.output_path.name} — {_format_size(result.optimized_size)}"
            new_cell, new_lbl = self._build_file_cell(
                new_text, result.output_path,
                DesignSystem.COLOR_SUCCESS,
                tr("results.open_output_tooltip"),
            )
            new_cell.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            new_cell.customContextMenuRequested.connect(
                lambda pos, r=result, w=new_cell: self._show_generated_file_context_menu(w, pos, r)
            )
        else:
            new_cell, new_lbl = self._build_file_cell(
                tr("results.skipped"), None,
                DesignSystem.COLOR_DANGER, "",
            )
            new_lbl.setToolTip(result.skipped_reason or "")
        h.addWidget(new_cell, 2)

        # Strategy
        preset_label = _preset_label(result.preset)
        strat_lbl = QLabel(preset_label)
        strat_lbl.setStyleSheet(DesignSystem.get_table_row_text_style().replace(DesignSystem.COLOR_TEXT, DesignSystem.COLOR_TEXT_SECONDARY))
        strat_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        strat_lbl.setMinimumWidth(80)
        h.addWidget(strat_lbl, 1)

        # Compression % — real value, positive or negative
        if not result.skipped and result.reduction_pct > 0:
            pct_color = (
                DesignSystem.COLOR_SUCCESS if result.reduction_pct >= 10
                else DesignSystem.COLOR_TEXT_SECONDARY
            )
            pct_lbl = QLabel(f"-{result.reduction_pct:.1f}%")
            pct_lbl.setStyleSheet(DesignSystem.get_table_summary_value_style(pct_color, False))
        elif not result.skipped and result.reduction_pct < 0:
            pct_lbl = QLabel(f"+{abs(result.reduction_pct):.1f}%")
            pct_lbl.setStyleSheet(DesignSystem.get_table_summary_value_style(DesignSystem.COLOR_DANGER, False))
            pct_lbl.setToolTip(
                tr("results.file_size_increased", pct=f"{abs(result.reduction_pct):.1f}")
            )
        elif not result.skipped:
            pct_lbl = QLabel("0.0%")
            pct_lbl.setStyleSheet(DesignSystem.get_table_summary_value_style(DesignSystem.COLOR_TEXT_SECONDARY, False))
        else:
            pct_lbl = QLabel("—")
            pct_lbl.setStyleSheet(DesignSystem.get_table_summary_value_style(DesignSystem.COLOR_TEXT_SECONDARY, False))
        pct_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pct_lbl.setMinimumWidth(90)
        h.addWidget(pct_lbl, 1)

        return row

    def _build_summary_row(self) -> QFrame | None:
        """Build a totals row."""
        ok = [r for r in self._results if not r.skipped]
        if not ok:
            return None

        summary = QFrame()
        # Remove the top border from the panel style as we will add it manually
        # to stop before the last column.
        panel_style = DesignSystem.get_table_summary_panel_style()
        panel_style = panel_style.replace(f"border-top: 2px solid {DesignSystem.COLOR_PRIMARY};", "border-top: none;")
        summary.setStyleSheet(panel_style)

        # Use a vertical layout to place the blue line row above the content row
        main_layout = QVBoxLayout(summary)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Line row: spans all columns
        line_row = QHBoxLayout()
        line_row.setContentsMargins(DesignSystem.SPACE_12, 0, DesignSystem.SPACE_12, 0)
        line_row.setSpacing(DesignSystem.SPACE_8)

        blue_line = QFrame()
        blue_line.setFixedHeight(2)
        blue_line.setStyleSheet(f"background-color: {DesignSystem.COLOR_PRIMARY}; border: none;")
        # Stretch 8 covers all columns (2+2+2+1+1)
        line_row.addWidget(blue_line, 8)

        main_layout.addLayout(line_row)

        # 2. Results/Values horizontal row
        h = QHBoxLayout()
        h.setContentsMargins(
            DesignSystem.SPACE_12, DesignSystem.SPACE_4,
            DesignSystem.SPACE_12, DesignSystem.SPACE_4,
        )
        h.setSpacing(DesignSystem.SPACE_8)

        bold = (
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
            f"border: none; background: transparent;"
        )
        mono = (
            f"font-family: {DesignSystem.FONT_FAMILY_MONO};"
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
            f"border: none; background: transparent;"
        )

        # Label
        total_lbl = QLabel(tr("results.total_row", count=len(self._results)))
        total_lbl.setStyleSheet(DesignSystem.get_table_summary_label_style())
        total_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        total_lbl.setMinimumWidth(120)
        h.addWidget(total_lbl, 2)

        # Total original
        total_orig = sum(r.original_size for r in ok)
        orig_lbl = QLabel(_format_size(total_orig))
        orig_lbl.setStyleSheet(DesignSystem.get_table_summary_value_style(DesignSystem.COLOR_TEXT, False))
        orig_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        orig_lbl.setMinimumWidth(150)
        h.addWidget(orig_lbl, 2)

        # Total optimized
        total_opt = sum(r.optimized_size for r in ok)
        opt_lbl = QLabel(_format_size(total_opt))
        opt_lbl.setStyleSheet(DesignSystem.get_table_summary_value_style(DesignSystem.COLOR_SUCCESS, False))
        opt_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        opt_lbl.setMinimumWidth(150)
        h.addWidget(opt_lbl, 2)

        # Strategy column
        unique_presets = set(r.preset for r in ok if r.preset is not None)
        if len(unique_presets) == 1:
            strat_text = _preset_label(next(iter(unique_presets)))
        elif len(unique_presets) > 1:
            strat_text = tr("results.mixed_strategy")
        else:
            strat_text = "—"
        strat_lbl = QLabel(strat_text)
        strat_lbl.setStyleSheet(DesignSystem.get_table_summary_value_style(DesignSystem.COLOR_TEXT_SECONDARY, False))
        strat_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        strat_lbl.setMinimumWidth(80)
        h.addWidget(strat_lbl, 1)

        # Average %
        avg_pct = ((total_orig - total_opt) / total_orig * 100) if total_orig else 0
        if avg_pct > 0:
            pct_lbl = QLabel(f"-{avg_pct:.1f}%")
            pct_lbl.setStyleSheet(DesignSystem.get_table_summary_value_style(DesignSystem.COLOR_SUCCESS, False))
        elif avg_pct < 0:
            pct_lbl = QLabel(f"+{abs(avg_pct):.1f}%")
            pct_lbl.setStyleSheet(DesignSystem.get_table_summary_value_style(DesignSystem.COLOR_DANGER, False))
        else:
            pct_lbl = QLabel("0.0%")
            pct_lbl.setStyleSheet(DesignSystem.get_table_summary_value_style(DesignSystem.COLOR_TEXT_SECONDARY, False))
        pct_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pct_lbl.setMinimumWidth(90)
        h.addWidget(pct_lbl, 1)

        main_layout.addLayout(h)
        return summary

    # ------------------------------------------------------------------
    # Tool results table (non-optimization)
    # ------------------------------------------------------------------

    def _rebuild_tool_table(self) -> None:
        """Build a results table for non-optimization tool results."""
        while self._table_container.count():
            item = self._table_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

        if not self._tool_results:
            return

        # Header row
        header = QFrame()
        header.setStyleSheet(DesignSystem.get_file_table_header_style())
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(
            DesignSystem.SPACE_12, DesignSystem.SPACE_4,
            DesignSystem.SPACE_12, DesignSystem.SPACE_4,
        )
        h_layout.setSpacing(DesignSystem.SPACE_8)

        for label_text, stretch, min_w, align in [
            (tr("results.header_file_path"), 2, 120, Qt.AlignmentFlag.AlignLeft),
            (tr("tool_results.col_input"), 3, 150, Qt.AlignmentFlag.AlignLeft),
            (tr("tool_results.col_output"), 3, 150, Qt.AlignmentFlag.AlignLeft),
            (tr("tool_results.col_status"), 1, 80, Qt.AlignmentFlag.AlignCenter),
        ]:
            lbl = QLabel(label_text)
            lbl.setStyleSheet(DesignSystem.get_table_header_cell_style(is_active=False))
            lbl.setAlignment(align | Qt.AlignmentFlag.AlignVCenter)
            lbl.setMinimumWidth(min_w)
            h_layout.addWidget(lbl, stretch)

        self._table_container.addWidget(header)

        # Data rows
        for i, result in enumerate(self._tool_results):
            row = self._build_tool_result_row(i, result)
            self._table_container.addWidget(row)

    def _build_tool_result_row(self, index: int, result: ToolResult) -> QFrame:
        """Build one row for a tool result."""
        even = index % 2 == 0

        row = QFrame()
        row.setStyleSheet(
            DesignSystem.get_file_table_row_optimized_style(even) if result.success
            else DesignSystem.get_file_table_row_style(even)
        )

        h = QHBoxLayout(row)
        h.setContentsMargins(
            DesignSystem.SPACE_12, DesignSystem.SPACE_2,
            DesignSystem.SPACE_12, DesignSystem.SPACE_2,
        )
        h.setSpacing(DesignSystem.SPACE_8)

        # File path (directory)
        if result.input_paths:
            dir_text = str(result.input_paths[0].parent)
        elif result.output_path:
            dir_text = str(result.output_path.parent)
        else:
            dir_text = "—"
        if len(dir_text) > 40:
            dir_text = "…" + dir_text[-37:]
        dir_lbl = QLabel(dir_text)
        dir_lbl.setStyleSheet(
            DesignSystem.get_table_row_text_style().replace(
                DesignSystem.COLOR_TEXT, DesignSystem.COLOR_TEXT_SECONDARY,
            )
        )
        dir_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        dir_lbl.setMinimumWidth(120)
        h.addWidget(dir_lbl, 2)

        # Original file(s) + eye icon
        if result.input_paths:
            if len(result.input_paths) == 1:
                inp_text = result.input_paths[0].name
                if result.original_size:
                    inp_text += f" — {_format_size(result.original_size)}"
                inp_path = result.input_paths[0]
            else:
                names = [p.name for p in result.input_paths]
                if len(names) > 3:
                    inp_text = f"{', '.join(names[:3])}… (+{len(names) - 3})"
                else:
                    inp_text = ", ".join(names)
                inp_path = None
        else:
            inp_text = "—"
            inp_path = None

        inp_cell, inp_lbl = self._build_file_cell(
            inp_text, inp_path,
            DesignSystem.COLOR_TEXT,
            tr("results.open_original_tooltip"),
        )
        inp_cell.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        inp_cell.customContextMenuRequested.connect(
            lambda pos, r=result, w=inp_cell: self._show_tool_original_context_menu(w, pos, r)
        )
        h.addWidget(inp_cell, 3)

        # Generated file + eye icon
        if result.success and result.output_path:
            out_text = result.output_path.name
            if result.output_size:
                out_text += f" — {_format_size(result.output_size)}"
            out_cell, out_lbl = self._build_file_cell(
                out_text, result.output_path,
                DesignSystem.COLOR_SUCCESS,
                tr("results.open_output_tooltip"),
            )
            out_cell.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            out_cell.customContextMenuRequested.connect(
                lambda pos, r=result, w=out_cell: self._show_tool_generated_context_menu(w, pos, r)
            )
        else:
            error_text = result.message or tr("tool_results.status_error")
            out_cell, _ = self._build_file_cell(
                error_text, None,
                DesignSystem.COLOR_DANGER, "",
            )
        h.addWidget(out_cell, 3)

        # Status
        if result.success:
            st_lbl = QLabel(tr("tool_results.status_ok"))
            st_lbl.setStyleSheet(
                DesignSystem.get_table_row_text_style().replace(
                    DesignSystem.COLOR_TEXT, DesignSystem.COLOR_SUCCESS,
                )
            )
        else:
            st_lbl = QLabel(tr("tool_results.status_error"))
            st_lbl.setStyleSheet(
                DesignSystem.get_table_row_text_style().replace(
                    DesignSystem.COLOR_TEXT, DesignSystem.COLOR_DANGER,
                )
            )
        st_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        st_lbl.setMinimumWidth(80)
        h.addWidget(st_lbl, 1)

        return row

    def _show_tool_original_context_menu(
        self, widget: QWidget, pos, result: ToolResult,
    ) -> None:
        """Context menu for original file column in tool results."""
        menu = QMenu(self)
        menu.setStyleSheet(DesignSystem.get_context_menu_style())

        if result.input_paths:
            view_action = menu.addAction(tr("results.view_details"))
            view_action.triggered.connect(
                lambda: self._show_details_for_file(result.input_paths[0])
            )
            folder_action = menu.addAction(tr("results.open_containing_folder"))
            folder_action.triggered.connect(
                lambda: self.open_folder_requested.emit(result.input_paths[0])
            )

        menu.exec(widget.mapToGlobal(pos))

    def _show_tool_generated_context_menu(
        self, widget: QWidget, pos, result: ToolResult,
    ) -> None:
        """Context menu for generated file column in tool results."""
        menu = QMenu(self)
        menu.setStyleSheet(DesignSystem.get_context_menu_style())

        if result.success and result.output_path:
            view_action = menu.addAction(tr("results.view_details"))
            view_action.triggered.connect(
                lambda: self._show_details_for_file(result.output_path)
            )
            folder_action = menu.addAction(tr("results.open_containing_folder"))
            folder_action.triggered.connect(
                lambda: self.open_folder_requested.emit(result.output_path)
            )

        menu.exec(widget.mapToGlobal(pos))

    def _clear_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_open_folder(self) -> None:
        if self._mode == "optimize":
            ok = [r for r in self._results if not r.skipped]
            if ok:
                self.open_folder_requested.emit(ok[0].output_path)
        else:
            for r in self._tool_results:
                if r.success and r.output_path:
                    self.open_folder_requested.emit(r.output_path)
                    return

    def _on_export_report(self) -> None:
        """Export results to a plain-text file."""
        if self._mode == "tool":
            self._export_tool_report()
            return
        if not self._results:
            return

        path, _ = QFileDialog.getSaveFileName(
            self, tr("results.export_dialog_title"), tr("results.export_default_name"),
            tr("results.export_filter"),
        )
        if not path:
            return

        ok = [r for r in self._results if not r.skipped]
        total_orig = sum(r.original_size for r in ok) if ok else 0
        total_opt = sum(r.optimized_size for r in ok) if ok else 0
        avg_pct = ((total_orig - total_opt) / total_orig * 100) if total_orig else 0

        lines: list[str] = []
        lines.append(tr("results.report_title"))
        lines.append("=" * 50)
        lines.append("")
        lines.append(tr("results.report_files_processed", count=len(self._results)))
        lines.append(tr("results.report_success", count=len(ok)))
        lines.append(tr("results.report_skipped", count=len(self._results) - len(ok)))
        lines.append("")

        if ok:
            lines.append(tr("results.report_total_original", size=_format_size(total_orig)))
            lines.append(tr("results.report_total_optimised", size=_format_size(total_opt)))
            lines.append(tr("results.report_total_saved", size=_format_size(total_orig - total_opt)))
            lines.append(tr("results.report_avg_reduction", pct=f"{avg_pct:.1f}"))
            lines.append("")

        lines.append("-" * 50)
        lines.append("")

        for r in self._results:
            lines.append(tr("results.report_input", path=r.input_path))
            if r.skipped:
                lines.append(tr("results.report_status_skipped", reason=r.skipped_reason or 'unknown reason'))
            else:
                lines.append(tr("results.report_output", path=r.output_path))
                lines.append(tr("results.report_strategy", name=_preset_label(r.preset)))
                lines.append(tr("results.report_original_size", size=_format_size(r.original_size)))
                lines.append(tr("results.report_optimised_size", size=_format_size(r.optimized_size)))
                lines.append(tr("results.report_reduction", pct=f"{r.reduction_pct:.1f}"))
            lines.append("")

        lines.append("-" * 50)
        lines.append(tr("results.report_footer"))

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
        except OSError:
            pass  # silently fail

    def _export_tool_report(self) -> None:
        """Export tool results to a plain-text file."""
        if not self._tool_results:
            return

        path, _ = QFileDialog.getSaveFileName(
            self, tr("results.export_dialog_title"), tr("results.export_default_name"),
            tr("results.export_filter"),
        )
        if not path:
            return

        successes = sum(1 for r in self._tool_results if r.success)
        total = len(self._tool_results)

        lines: list[str] = []
        lines.append(tr("tool_results.report_title"))
        lines.append("=" * 50)
        lines.append("")
        lines.append(tr("tool_results.report_files_processed", count=total))
        lines.append(tr("tool_results.report_success", count=successes))
        lines.append(tr("tool_results.report_failed", count=total - successes))
        lines.append("")
        lines.append("-" * 50)
        lines.append("")

        for r in self._tool_results:
            if r.input_paths:
                for p in r.input_paths:
                    lines.append(tr("results.report_input", path=p))
            if r.success and r.output_path:
                lines.append(tr("results.report_output", path=r.output_path))
                lines.append(tr("tool_results.report_status_ok"))
            else:
                lines.append(tr("tool_results.report_status_error", reason=r.message or ""))
            lines.append("")

        lines.append("-" * 50)
        lines.append(tr("results.report_footer"))

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
        except OSError:
            pass  # silently fail

    # ------------------------------------------------------------------
    # Context menu
    # ------------------------------------------------------------------

    def _show_row_context_menu(
        self, widget: QWidget, pos, result: OptimizeResult,
    ) -> None:
        """Per-row context menu with View Details."""
        menu = QMenu(self)
        menu.setStyleSheet(DesignSystem.get_context_menu_style())

        view_action = menu.addAction(tr("results.view_details"))
        view_action.triggered.connect(
            lambda: self._show_details_for_file(result.input_path)
        )

        if not result.skipped:
            menu.addSeparator()
            open_action = menu.addAction(tr("results.open_optimised_file"))
            open_action.triggered.connect(
                lambda: self.open_file_requested.emit(result.output_path)
            )
            folder_action = menu.addAction(tr("results.open_containing_folder"))
            folder_action.triggered.connect(
                lambda: self.open_folder_requested.emit(result.output_path)
            )

        menu.exec(widget.mapToGlobal(pos))

    def _show_original_file_context_menu(
        self, widget: QWidget, pos, result: OptimizeResult,
    ) -> None:
        """Context menu for original file column."""
        menu = QMenu(self)
        menu.setStyleSheet(DesignSystem.get_context_menu_style())

        view_action = menu.addAction(tr("results.view_details"))
        view_action.triggered.connect(
            lambda: self._show_details_for_file(result.input_path)
        )

        menu.exec(widget.mapToGlobal(pos))

    def _show_generated_file_context_menu(
        self, widget: QWidget, pos, result: OptimizeResult,
    ) -> None:
        """Context menu for generated file column."""
        menu = QMenu(self)
        menu.setStyleSheet(DesignSystem.get_context_menu_style())

        view_action = menu.addAction(tr("results.view_details"))
        view_action.triggered.connect(
            lambda: self._show_details_for_file(result.output_path)
        )

        menu.exec(widget.mapToGlobal(pos))

    def _show_details_for_file(self, path: Path) -> None:
        """Open the details dialog for a specific file."""
        from safetool_pdf_core.analyzer import analyze
        from safetool_pdf_desktop.dialogs.details_dialog import DetailsDialog

        try:
            analysis = analyze(path)
        except Exception:
            return
        dlg = DetailsDialog(analysis, parent=self)
        dlg.exec()
