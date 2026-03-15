# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Screen 2: Analysis → Per-file strategy comparison → Optimization.

Redesigned flow:
  - Analyses ALL selected files.
  - Estimates savings PER FILE for Lossless/Balanced/Maximum (+ Custom on demand).
  - Always-visible legend explaining each strategy honestly.
  - Table with per-file strategy selection and preview icons.
  - "Apply to all" combo in table header for bulk selection.
  - Auto-selects best compression per file; user reviews.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QDesktopServices, QFontMetrics, QPainter
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QGraphicsOpacityEffect, QHBoxLayout,
    QLabel, QMenu, QMessageBox, QProgressBar, QPushButton, QScrollArea,
    QSizePolicy, QSlider, QSpinBox, QStackedWidget, QToolButton,
    QVBoxLayout, QWidget
)

from safetool_pdf_core.analyzer import analyze
from safetool_pdf_core.models import (
    AnalysisResult, CleanupOptions, GhostscriptOptions, LosslessOptions,
    LossyImageOptions, OptimizeOptions, OptimizeResult, PreservationMode,
    PresetName, ProgressInfo
)
from safetool_pdf_core.tools.optimize import preset_by_name, preset_requires_gs
from safetool_pdf_core.gs_detect import gs_available
from safetool_pdf_core.tools.optimize import optimize
from safetool_pdf_desktop.settings import OUTPUT_SUFFIX as OUTPUT_SUFFIX_KEY, load_setting
from safetool_pdf_desktop.styles.design_system import DesignSystem
from safetool_pdf_desktop.styles.icons import icon_manager
from safetool_pdf_desktop.workers.base_worker import BaseWorker
from i18n import tr

_logger = logging.getLogger(__name__)

# ── Helpers ──────────────────────────────────────────────────────────

def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"

_PRESET_META: dict[PresetName, dict] = {
    PresetName.LOSSLESS: {
        "label_key": "presets.lossless.label",
        "icon": "shield-check",
        "color": DesignSystem.COLOR_SUCCESS,
        "desc_key": "presets.lossless.desc",
    },
    PresetName.MODERATE: {
        "label_key": "presets.moderate.label",
        "icon": "scale-balance",
        "color": DesignSystem.COLOR_PRIMARY,
        "desc_key": "presets.moderate.desc",
    },
    PresetName.AGGRESSIVE: {
        "label_key": "presets.aggressive.label",
        "icon": "rocket-launch",
        "color": DesignSystem.COLOR_DANGER,
        "desc_key": "presets.aggressive.desc",
    },
    PresetName.CUSTOM: {
        "label_key": "presets.custom.label",
        "icon": "tune",
        "color": DesignSystem.COLOR_SECONDARY,
        "desc_key": "presets.custom.desc",
    },
}


def _preset_label(preset: PresetName) -> str:
    """Get the translated label for a preset."""
    meta = _PRESET_META.get(preset)
    return tr(meta["label_key"]) if meta else "—"


def _preset_desc(preset: PresetName) -> str:
    """Get the translated description for a preset."""
    meta = _PRESET_META.get(preset)
    return tr(meta["desc_key"]) if meta else ""

# ── Workers ──────────────────────────────────────────────────────────

class AnalysisBatchWorker(BaseWorker):
    all_done = Signal(object)
    def __init__(self, files: list[Path], parent=None) -> None:
        super().__init__(parent)
        self._files = files
    def run(self) -> None:
        results = []
        for i, path in enumerate(self._files):
            if self._cancel.is_set(): return
            self.progress_text.emit(tr("strategy.analysing_file", current=i + 1, total=len(self._files), filename=path.name))
            try: results.append(analyze(path))
            except Exception: results.append(None)
        if not self._cancel.is_set(): self.all_done.emit(results)

class EstimationBatchWorker(BaseWorker):
    file_preset_done = Signal(int, object, object)
    all_done = Signal(object)          # dict[int, dict[PresetName, OptimizeResult|None]]
    temp_dir_ready = Signal(object)     # Path — caller owns cleanup
    PRESETS = [PresetName.LOSSLESS, PresetName.MODERATE, PresetName.AGGRESSIVE]
    def __init__(self, files: list[Path], presets: list[PresetName] | None = None, parent=None) -> None:
        super().__init__(parent)
        self._files = files
        self._presets = presets or self.PRESETS
    def run(self) -> None:
        import tempfile
        tmp_dir = Path(tempfile.mkdtemp(prefix="safetool_pdf_est_"))
        self.temp_dir_ready.emit(tmp_dir)
        all_results: dict[int, dict] = {}
        for fi, path in enumerate(self._files):
            file_results: dict[PresetName, OptimizeResult | None] = {}
            for preset in self._presets:
                if self._cancel.is_set(): return
                self.progress_text.emit(tr("strategy.estimating_status", preset=_preset_label(preset), filename=path.name, current=fi + 1, total=len(self._files)))
                try:
                    res = optimize(path, preset_by_name(preset), output_dir=tmp_dir)
                    file_results[preset] = res
                    self.file_preset_done.emit(fi, preset, res)
                except Exception:
                    file_results[preset] = None
                    self.file_preset_done.emit(fi, preset, None)
            all_results[fi] = file_results
        if not self._cancel.is_set(): self.all_done.emit(all_results)

class CustomEstimationWorker(BaseWorker):
    file_done = Signal(int, object)
    all_done = Signal(object)
    temp_dir_ready = Signal(object)
    def __init__(self, files: list[Path], options: OptimizeOptions, output_dir: Path | None = None, parent=None) -> None:
        super().__init__(parent)
        self._files = files
        self._options = options
        self._output_dir = output_dir
    def run(self) -> None:
        import tempfile
        tmp_dir = self._output_dir or Path(tempfile.mkdtemp(prefix="safetool_pdf_cest_"))
        if not self._output_dir:
            self.temp_dir_ready.emit(tmp_dir)
        results: dict[int, OptimizeResult | None] = {}
        for fi, path in enumerate(self._files):
            if self._cancel.is_set(): return
            self.progress_text.emit(tr("strategy.estimating_status", preset=tr("presets.custom.label"), filename=path.name, current=fi + 1, total=len(self._files)))
            try:
                res = optimize(path, self._options, output_dir=tmp_dir)
                results[fi] = res
                self.file_done.emit(fi, res)
            except Exception:
                results[fi] = None
                self.file_done.emit(fi, None)
        if not self._cancel.is_set(): self.all_done.emit(results)

class BatchOptimizeWorker(BaseWorker):
    progress = Signal(object)
    finished = Signal(object)
    def __init__(self, file_options: list[tuple[Path, OptimizeOptions]], parent=None) -> None:
        super().__init__(parent)
        self._file_options = file_options
    def run(self) -> None:
        results = []
        total = len(self._file_options)
        for idx, (path, opts) in enumerate(self._file_options, 1):
            if self._cancel.is_set(): break
            def _cb(info, _idx=idx, _total=total):
                info.file_index, info.file_total = _idx, _total
                self.progress.emit(info)
            try:
                res = optimize(path, options=opts, progress_cb=_cb, cancel=self._cancel)
                results.append(res)
            except Exception as exc:
                results.append(OptimizeResult(input_path=path, output_path=path, preset=opts.preset, skipped=True, skipped_reason=str(exc)))
        self.finished.emit(results)

# ── UI Components ────────────────────────────────────────────────────

# Sentinel used in _file_presets to mean "do not optimise this file".
_SKIP = "skip"


class ElidedLabel(QLabel):
    """A QLabel that automatically elides its text with '...' if it overflows."""
    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setMinimumWidth(1) # Allow shrinking beyond sizeHint

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        metrics = QFontMetrics(self.font())
        elided_text = metrics.elidedText(self.text(), Qt.TextElideMode.ElideRight, self.width())
        painter.drawText(self.rect(), self.alignment(), elided_text)
        painter.end()


class CustomOptimizationPanel(QFrame):
    """Compact custom settings panel — professional design, minimal vertical space."""

    estimate_clicked = Signal(OptimizeOptions)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        self.setStyleSheet(DesignSystem.get_custom_panel_style())
        main = QVBoxLayout(self)
        main.setContentsMargins(16, 12, 16, 20)
        main.setSpacing(14)

        # Header: Title + Discrete hide button
        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 4)
        
        ic_box = QLabel()
        icon_manager.set_label_icon(ic_box, "tune", color=DesignSystem.COLOR_PRIMARY, size=16)
        hdr.addWidget(ic_box)
        
        title = QLabel(tr("custom_panel.title"))
        title.setStyleSheet(DesignSystem.get_custom_section_header_style())
        hdr.addWidget(title)
        hdr.addStretch()

        self._close_btn = QToolButton()
        self._close_btn.setToolTip(tr("custom_panel.hide_tooltip"))
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.setStyleSheet(DesignSystem.get_icon_button_style())
        icon_manager.set_button_icon(self._close_btn, "chevron-up", color=DesignSystem.COLOR_TEXT_SECONDARY, size=18)
        self._close_btn.clicked.connect(self.hide)
        hdr.addWidget(self._close_btn)
        main.addLayout(hdr)

        # Helper to create a vertical slider group
        def _slider_group(title: str, range_min: int, range_max: int, default: int, suffix: str = ""):
            v_lay = QVBoxLayout()
            v_lay.setSpacing(2)
            hdr = QHBoxLayout()
            lbl = QLabel(title)
            lbl.setStyleSheet(DesignSystem.get_custom_section_header_style())
            val_lbl = QLabel(f"{default}{suffix}")
            val_lbl.setStyleSheet(f"font-weight: {DesignSystem.FONT_WEIGHT_BOLD}; color: {DesignSystem.COLOR_PRIMARY};")
            hdr.addWidget(lbl)
            hdr.addStretch()
            hdr.addWidget(val_lbl)
            v_lay.addLayout(hdr)
            
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(range_min, range_max)
            slider.setValue(default)
            slider.setStyleSheet(DesignSystem.get_slider_style())
            slider.setFixedHeight(20)
            slider.valueChanged.connect(lambda v: val_lbl.setText(f"{v}{suffix}"))
            v_lay.addWidget(slider)
            return v_lay, slider, lbl, val_lbl

        # Row 1: Images (Master Checkbox + DPI + Quality)
        img_row = QHBoxLayout()
        img_row.setSpacing(20)
        
        self._enable_images = QCheckBox(tr("custom_panel.compress_images"))
        self._enable_images.setToolTip(tr("custom_panel.compress_images_tooltip"))
        self._enable_images.setStyleSheet(DesignSystem.get_checkbox_style())
        self._enable_images.setFixedWidth(160)
        img_row.addWidget(self._enable_images)
        
        dpi_v, self._dpi_slider, self._dpi_lbl, self._dpi_vlbl = _slider_group(tr("custom_panel.target_dpi"), 72, 600, 150)
        self._dpi_slider.setToolTip(tr("custom_panel.target_dpi_tooltip"))
        img_row.addLayout(dpi_v, 1)
        
        qual_v, self._qual_slider, self._qual_lbl, self._qual_vlbl = _slider_group(tr("custom_panel.jpeg_quality"), 10, 100, 80, "%")
        self._qual_slider.setToolTip(tr("custom_panel.jpeg_quality_tooltip"))
        img_row.addLayout(qual_v, 1)
        main.addLayout(img_row)

        # Row 2: Ghostscript (Master Checkbox + Sub-options)
        gs_row = QHBoxLayout()
        gs_row.setSpacing(20)
        
        self._enable_gs = QCheckBox(tr("custom_panel.ghostscript_process"))
        self._enable_gs.setToolTip(tr("custom_panel.ghostscript_tooltip"))
        self._enable_gs.setStyleSheet(DesignSystem.get_checkbox_style())
        self._enable_gs.setFixedWidth(160)
        gs_row.addWidget(self._enable_gs)
        
        gs_opts = QHBoxLayout()
        gs_opts.setSpacing(16)
        self._font_subset = QCheckBox(tr("custom_panel.subset_fonts"))
        self._font_subset.setToolTip(tr("custom_panel.subset_fonts_tooltip"))
        self._font_subset.setStyleSheet(DesignSystem.get_checkbox_style())
        gs_opts.addWidget(self._font_subset)
        
        self._full_rewrite = QCheckBox(tr("custom_panel.clean_rewrites"))
        self._full_rewrite.setToolTip(tr("custom_panel.clean_rewrites_tooltip"))
        self._full_rewrite.setStyleSheet(DesignSystem.get_checkbox_style())
        gs_opts.addWidget(self._full_rewrite)
        gs_opts.addStretch()
        gs_row.addLayout(gs_opts, 2)
        main.addLayout(gs_row)

        # Row 3: Cleanup & Action
        btm_row = QHBoxLayout()
        btm_row.setSpacing(20)
        
        cl_label = QLabel(tr("custom_panel.cleanup_label"))
        cl_label.setStyleSheet(DesignSystem.get_custom_section_header_style())
        cl_label.setFixedWidth(160)
        btm_row.addWidget(cl_label)

        cl_opts = QHBoxLayout()
        cl_opts.setSpacing(16)
        self._remove_metadata = QCheckBox(tr("custom_panel.metadata"))
        self._remove_metadata.setToolTip(tr("custom_panel.metadata_tooltip"))
        self._remove_metadata.setStyleSheet(DesignSystem.get_checkbox_style())
        cl_opts.addWidget(self._remove_metadata)
        
        self._flatten_forms = QCheckBox(tr("custom_panel.forms"))
        self._flatten_forms.setToolTip(tr("custom_panel.forms_tooltip"))
        self._flatten_forms.setStyleSheet(DesignSystem.get_checkbox_style())
        cl_opts.addWidget(self._flatten_forms)
        
        self._remove_js = QCheckBox(tr("custom_panel.js_scripts"))
        self._remove_js.setToolTip(tr("custom_panel.js_scripts_tooltip"))
        self._remove_js.setStyleSheet(DesignSystem.get_checkbox_style())
        cl_opts.addWidget(self._remove_js)
        cl_opts.addStretch()
        btm_row.addLayout(cl_opts, 2)
        
        self._est_btn = QPushButton(tr("custom_panel.estimate_btn"))
        self._est_btn.setToolTip(tr("custom_panel.estimate_tooltip"))
        icon_manager.set_button_icon(self._est_btn, "magnify", size=16)
        self._est_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        self._est_btn.setFixedHeight(32)
        btm_row.addWidget(self._est_btn)
        main.addLayout(btm_row)
        
        main.addStretch() # Ensure widgets are pushed top so they don't stretch to the bottom border

        # Logic: Enable/Disable children based on master checkboxes
        def _update_images_state(enabled: bool):
            self._dpi_slider.setEnabled(enabled)
            self._qual_slider.setEnabled(enabled)
            opacity = 1.0 if enabled else 0.4
            # Dim the labels too for better visual feedback
            for w in [self._dpi_lbl, self._dpi_vlbl, self._qual_lbl, self._qual_vlbl]:
                eff = QGraphicsOpacityEffect(w)
                eff.setOpacity(opacity)
                w.setGraphicsEffect(eff)

        def _update_gs_state(enabled: bool):
            self._font_subset.setEnabled(enabled)
            self._full_rewrite.setEnabled(enabled)

        self._enable_images.toggled.connect(_update_images_state)
        self._enable_gs.toggled.connect(_update_gs_state)
        self._est_btn.clicked.connect(lambda: self.estimate_clicked.emit(self.get_options()))
        
        # Init state
        self._enable_images.setChecked(False)
        self._enable_gs.setChecked(False)
        _update_images_state(False)
        _update_gs_state(False)

    def get_options(self) -> OptimizeOptions:
        return OptimizeOptions(
            preset=PresetName.CUSTOM,
            lossy_images=LossyImageOptions(
                enabled=self._enable_images.isChecked(),
                target_dpi=self._dpi_slider.value(),
                jpeg_quality=self._qual_slider.value(),
            ),
            ghostscript=GhostscriptOptions(
                enabled=self._enable_gs.isChecked(),
                font_subsetting=self._font_subset.isChecked(),
                full_rewrite=self._full_rewrite.isChecked(),
            ),
            cleanup=CleanupOptions(
                remove_metadata=self._remove_metadata.isChecked(),
                flatten_forms=self._flatten_forms.isChecked(),
                remove_javascript=self._remove_js.isChecked(),
            ),
        )

    def set_gs_available(self, available: bool) -> None:
        """Enable or disable the Ghostscript options based on availability."""
        self._enable_gs.setEnabled(available)
        if not available:
            self._enable_gs.setChecked(False)
            self._enable_gs.setToolTip(tr("strategy.gs_required_tooltip"))
        else:
            self._enable_gs.setToolTip(tr("custom_panel.ghostscript_tooltip"))


# ── Main Screen ──────────────────────────────────────────────────────

class StrategyScreen(QWidget):
    go_back = Signal()
    optimization_complete = Signal(list, list)
    open_file_requested = Signal(Path)
    open_folder_requested = Signal(Path)
    STRATEGY_ORDER = [PresetName.LOSSLESS, PresetName.MODERATE, PresetName.AGGRESSIVE, PresetName.CUSTOM]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._files: list[Path] = []
        self._analyses: list[AnalysisResult | None] = []
        self._estimations: dict[int, dict[PresetName, OptimizeResult | None]] = {}
        # Value is a PresetName, or _SKIP for "do not optimise"
        self._file_presets: dict[int, PresetName | str] = {}
        self._gs_available: bool = gs_available()
        self._analysis_worker = None
        self._estimation_worker = None
        self._custom_estimation_worker = None
        self._batch_worker = None
        self._est_temp_dir: Path | None = None  # kept alive for preview
        self._build_ui()

    # ── Cleanup ──────────────────────────────────────────────────────

    def _cleanup_temp_dir(self) -> None:
        if self._est_temp_dir and self._est_temp_dir.exists():
            shutil.rmtree(self._est_temp_dir, ignore_errors=True)
            self._est_temp_dir = None

    def hideEvent(self, event) -> None:  # noqa: N802
        super().hideEvent(event)

    def __del__(self) -> None:
        self._cleanup_temp_dir()

    # ── Page builders ────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self._inner_stack = QStackedWidget()
        root.addWidget(self._inner_stack)
        self._inner_stack.addWidget(self._build_analyzing_page())
        self._inner_stack.addWidget(self._build_comparison_page())
        self._inner_stack.addWidget(self._build_optimizing_page())

    def _build_analyzing_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(DesignSystem.SPACE_16)
        lay.addStretch()
        ic = QLabel()
        icon_manager.set_label_icon(ic, "magnify", color=DesignSystem.COLOR_PRIMARY, size=48)
        lay.addWidget(ic, 0, Qt.AlignmentFlag.AlignCenter)
        self._at = QLabel(tr("strategy.analysing_title"))
        self._at.setStyleSheet(DesignSystem.get_strategy_header_text_style())
        lay.addWidget(self._at, 0, Qt.AlignmentFlag.AlignCenter)
        self._as = QLabel(tr("strategy.analysing_status"))
        self._as.setStyleSheet(DesignSystem.get_strategy_info_text_style())
        lay.addWidget(self._as, 0, Qt.AlignmentFlag.AlignCenter)
        self._ap = QProgressBar()
        self._ap.setRange(0, 0)
        self._ap.setStyleSheet(DesignSystem.get_progressbar_style())
        self._ap.setFixedWidth(400)
        lay.addWidget(self._ap, 0, Qt.AlignmentFlag.AlignCenter)
        lay.addStretch()
        cancel = QPushButton(tr("strategy.cancel"))
        cancel.setStyleSheet(DesignSystem.get_secondary_button_style())
        cancel.clicked.connect(self._on_cancel_analysis)
        lay.addWidget(cancel, 0, Qt.AlignmentFlag.AlignCenter)
        lay.addSpacing(40)
        return page

    def _build_comparison_page(self) -> QWidget:
        page = QWidget()
        page_lay = QVBoxLayout(page)
        page_lay.setContentsMargins(0, 0, 0, 0)
        page_lay.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(DesignSystem.get_scroll_area_style())
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(24, 16, 24, 24)
        lay.setSpacing(16)

        # ── Top bar: Back + file summary
        top = QHBoxLayout()
        back = QPushButton(tr("strategy.back"))
        icon_manager.set_button_icon(back, "arrow-left", size=16)
        back.setStyleSheet(DesignSystem.get_secondary_button_style())
        back.clicked.connect(self.go_back.emit)
        top.addWidget(back)
        top.addSpacing(16)
        self._file_info_label = QLabel("...")
        self._file_info_label.setStyleSheet(DesignSystem.get_strategy_header_text_style())
        top.addWidget(self._file_info_label, 1)
        top.addStretch()

        apply_all_lbl = QLabel(tr("strategy.apply_to_all"))
        apply_all_lbl.setStyleSheet(DesignSystem.get_strategy_info_text_style())
        top.addWidget(apply_all_lbl)

        self._apply_all_combo = QComboBox()
        self._apply_all_combo.setStyleSheet(DesignSystem.get_apply_all_combo_style())
        self._apply_all_combo.addItem(tr("strategy.select_placeholder"), None)
        for pr in self._get_presets_in_table():
            if preset_requires_gs(pr) and not self._gs_available:
                continue
            self._apply_all_combo.addItem(_preset_label(pr), pr)
        self._apply_all_combo.addItem(tr("strategy.skip_all"), _SKIP)
        self._apply_all_combo.setToolTip(tr("strategy.apply_all_tooltip"))
        self._apply_all_combo.currentIndexChanged.connect(
            lambda idx: self._on_apply_all(self._apply_all_combo, idx)
        )
        top.addWidget(self._apply_all_combo)

        lay.addLayout(top)

        # ── Always-visible strategy legend
        lay.addWidget(self._build_strategy_legend())

        # ── Info alert: auto-selection explanation
        alert = QFrame()
        alert.setStyleSheet(DesignSystem.get_info_alert_style())
        al = QHBoxLayout(alert)
        al.setContentsMargins(12, 8, 12, 8)
        ai = QLabel()
        icon_manager.set_label_icon(ai, "information", color=DesignSystem.COLOR_INFO, size=20)
        al.addWidget(ai)
        alert_text = QLabel(tr("strategy.info_alert"))
        alert_text.setWordWrap(True)
        alert_text.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px; "
            f"color: {DesignSystem.COLOR_INFO_TEXT}; border: none; background: transparent;"
        )
        al.addWidget(alert_text, 1)
        lay.addWidget(alert)

        # ── GS warning banner (shown when Ghostscript is not installed)
        self._gs_warning = QFrame()
        self._gs_warning.setStyleSheet(DesignSystem.get_warning_alert_style())
        gw_lay = QHBoxLayout(self._gs_warning)
        gw_lay.setContentsMargins(12, 8, 12, 8)
        gw_icon = QLabel()
        icon_manager.set_label_icon(gw_icon, "information", color=DesignSystem.COLOR_WARNING_TEXT, size=20)
        gw_lay.addWidget(gw_icon)
        gw_text = QLabel(tr("strategy.gs_not_available_warning"))
        gw_text.setWordWrap(True)
        gw_text.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px; "
            f"color: {DesignSystem.COLOR_WARNING_TEXT}; border: none; background: transparent;"
        )
        gw_lay.addWidget(gw_text, 1)
        self._gs_warning.setVisible(not self._gs_available)
        lay.addWidget(self._gs_warning)

        # ── Custom panel (hidden until Custom is chosen for any file)
        self._custom_panel = CustomOptimizationPanel()
        self._custom_panel.setVisible(False)
        self._custom_panel.estimate_clicked.connect(self._on_custom_estimate)
        lay.addWidget(self._custom_panel)

        # ── Estimation table
        table_frame = QFrame()
        table_frame.setStyleSheet(DesignSystem.get_estimation_table_container_style())
        tf_lay = QVBoxLayout(table_frame)
        tf_lay.setContentsMargins(0, 0, 0, 0)
        self._table_container = QVBoxLayout()
        self._table_container.setSpacing(0)
        tf_lay.addLayout(self._table_container)
        lay.addWidget(table_frame)

        # ── Optimize button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._optimize_btn = QPushButton(tr("strategy.optimize_all"))
        icon_manager.set_button_icon(
            self._optimize_btn, "rocket-launch",
            color=DesignSystem.COLOR_PRIMARY_TEXT, size=18,
        )
        self._optimize_btn.setStyleSheet(DesignSystem.get_primary_button_style())
        self._optimize_btn.clicked.connect(self._on_optimize_clicked)
        btn_row.addWidget(self._optimize_btn)
        lay.addLayout(btn_row)
        lay.addStretch()

        scroll.setWidget(content)
        page_lay.addWidget(scroll)
        return page

    def _build_strategy_legend(self) -> QFrame:
        """Always-visible horizontal legend explaining each strategy."""
        outer = QFrame()
        outer.setStyleSheet(DesignSystem.get_strategy_legend_card_style())
        outer_lay = QVBoxLayout(outer)
        outer_lay.setContentsMargins(12, 10, 12, 10)
        outer_lay.setSpacing(8)

        row = QHBoxLayout()
        row.setSpacing(10)
        for preset in (PresetName.LOSSLESS, PresetName.MODERATE, PresetName.AGGRESSIVE, PresetName.CUSTOM):
            meta = _PRESET_META[preset]
            card = QFrame()
            card.setStyleSheet(DesignSystem.get_strategy_legend_item_style(meta["color"]))
            if preset == PresetName.CUSTOM:
                card.setToolTip(tr("strategy.custom_tooltip"))
            cl = QVBoxLayout(card)
            cl.setContentsMargins(10, 6, 10, 6)
            cl.setSpacing(2)

            hdr = QHBoxLayout()
            hdr.setSpacing(6)
            ic = QLabel()
            icon_manager.set_label_icon(ic, meta["icon"], color=meta["color"], size=16)
            hdr.addWidget(ic)
            name = QLabel(tr(meta["label_key"]))
            name.setStyleSheet(
                f"font-size: {DesignSystem.FONT_SIZE_SM}px; "
                f"font-weight: {DesignSystem.FONT_WEIGHT_BOLD}; "
                f"color: {DesignSystem.COLOR_TEXT}; border: none; background: transparent;"
            )
            hdr.addWidget(name)
            hdr.addStretch()
            cl.addLayout(hdr)

            desc = QLabel(tr(meta["desc_key"]))
            desc.setWordWrap(True)
            desc.setStyleSheet(
                f"font-size: {DesignSystem.FONT_SIZE_XS}px; "
                f"color: {DesignSystem.COLOR_TEXT_SECONDARY}; "
                f"border: none; background: transparent;"
            )
            cl.addWidget(desc)
            row.addWidget(card, 1)
        outer_lay.addLayout(row)
        return outer

    def _build_optimizing_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(16)
        lay.addStretch()
        ic = QLabel()
        icon_manager.set_label_icon(ic, "compress", color=DesignSystem.COLOR_PRIMARY, size=48)
        lay.addWidget(ic, 0, Qt.AlignmentFlag.AlignCenter)
        self._ot = QLabel(tr("strategy.optimising_title"))
        self._ot.setStyleSheet(DesignSystem.get_strategy_header_text_style())
        lay.addWidget(self._ot, 0, Qt.AlignmentFlag.AlignCenter)
        self._os = QLabel("")
        self._os.setStyleSheet(DesignSystem.get_strategy_info_text_style())
        lay.addWidget(self._os, 0, Qt.AlignmentFlag.AlignCenter)
        self._op = QProgressBar()
        self._op.setRange(0, 100)
        self._op.setStyleSheet(DesignSystem.get_progressbar_style())
        self._op.setFixedWidth(400)
        lay.addWidget(self._op, 0, Qt.AlignmentFlag.AlignCenter)
        lay.addStretch()
        cancel = QPushButton(tr("strategy.cancel"))
        cancel.setStyleSheet(DesignSystem.get_secondary_button_style())
        cancel.clicked.connect(self._on_cancel_optimize)
        lay.addWidget(cancel, 0, Qt.AlignmentFlag.AlignCenter)
        lay.addSpacing(40)
        return page

    # ── Public API ───────────────────────────────────────────────────

    def set_files(self, files: list[Path]) -> None:
        # Cancel any running workers before starting new ones
        for w in (self._analysis_worker, self._estimation_worker,
                  self._custom_estimation_worker, self._batch_worker):
            if w is not None and w.isRunning():
                w.request_cancel()
                w.wait(3000)
        self._cleanup_temp_dir()
        self._files = files
        self._analyses = []
        self._estimations = {}
        self._file_presets = {}
        self._gs_available = gs_available()
        self._custom_panel.setVisible(False)
        self._custom_panel.set_gs_available(self._gs_available)
        self._gs_warning.setVisible(not self._gs_available)
        self._apply_all_combo.blockSignals(True)
        self._apply_all_combo.clear()
        self._apply_all_combo.addItem(tr("strategy.select_placeholder"), None)
        for pr in self._get_presets_in_table():
            if preset_requires_gs(pr) and not self._gs_available:
                continue
            self._apply_all_combo.addItem(_preset_label(pr), pr)
        self._apply_all_combo.addItem(tr("strategy.skip_all"), _SKIP)
        self._apply_all_combo.setCurrentIndex(0)
        self._apply_all_combo.blockSignals(False)
        self._inner_stack.setCurrentIndex(0)
        QTimer.singleShot(0, self._start_analysis_flow)

    # ── Analysis / estimation flow ───────────────────────────────────

    def _start_analysis_flow(self) -> None:
        self._at.setText(tr("strategy.analysing_n_files", count=len(self._files)))
        self._analysis_worker = AnalysisBatchWorker(self._files)
        self._analysis_worker.progress_text.connect(self._as.setText)
        self._analysis_worker.all_done.connect(self._on_analysis_done)
        self._analysis_worker.start()

    def _on_analysis_done(self, results: list) -> None:
        self._analyses = results
        self._at.setText(tr("strategy.estimating_title"))
        estimation_presets = [
            p for p in EstimationBatchWorker.PRESETS
            if not preset_requires_gs(p) or self._gs_available
        ]
        self._estimation_worker = EstimationBatchWorker(self._files, presets=estimation_presets)
        self._estimation_worker.progress_text.connect(self._as.setText)
        self._estimation_worker.file_preset_done.connect(self._on_est_done)
        self._estimation_worker.temp_dir_ready.connect(self._on_temp_dir)
        self._estimation_worker.all_done.connect(self._on_all_estimations_done)
        self._estimation_worker.start()

    def _on_temp_dir(self, tmp_dir: Path) -> None:
        self._est_temp_dir = tmp_dir

    def _on_est_done(self, fi: int, preset: PresetName, res: OptimizeResult | None) -> None:
        if fi not in self._estimations:
            self._estimations[fi] = {}
        self._estimations[fi][preset] = res

    def _on_all_estimations_done(self, results: dict) -> None:
        self._estimations = results
        self._auto_select_best()
        self._populate_info()
        self._inner_stack.setCurrentIndex(1)

    def _auto_select_best(self) -> None:
        """Select the preset with highest reduction_pct per file."""
        for i in range(len(self._files)):
            best_p: PresetName | str = _SKIP
            best_r = 0.0
            for pr in (PresetName.LOSSLESS, PresetName.MODERATE, PresetName.AGGRESSIVE):
                if preset_requires_gs(pr) and not self._gs_available:
                    continue
                est = self._estimations.get(i, {}).get(pr)
                if est and not est.skipped and est.reduction_pct > best_r:
                    best_r = est.reduction_pct
                    best_p = pr
            self._file_presets[i] = best_p

    def _populate_info(self) -> None:
        total_sz = sum(a.file_size for a in self._analyses if a)
        self._file_info_label.setText(
            tr("strategy.files_selected_info", count=len(self._files), size=_format_size(total_sz))
        )
        self._rebuild_table()

    # ── Table ────────────────────────────────────────────────────────

    def _get_presets_in_table(self) -> list[PresetName]:
        """Return the preset columns to show — always includes Custom."""
        return [PresetName.LOSSLESS, PresetName.MODERATE, PresetName.AGGRESSIVE, PresetName.CUSTOM]

    def _rebuild_table(self) -> None:
        # Clear existing rows
        while self._table_container.count():
            item = self._table_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        presets_in_table = self._get_presets_in_table()

        # ── Header row
        header = QFrame()
        header.setStyleSheet(DesignSystem.get_file_table_header_style())
        hl = QHBoxLayout(header)
        hl.setContentsMargins(12, 6, 12, 6)

        file_lbl = QLabel(tr("strategy.file_header"))
        file_lbl.setStyleSheet(DesignSystem.get_table_header_cell_style())
        hl.addWidget(file_lbl, 3)

        for pr in presets_in_table:
            lbl = QLabel(_preset_label(pr).upper())
            lbl.setStyleSheet(DesignSystem.get_table_header_cell_style())
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hl.addWidget(lbl, 2)

        # "Skip" column header
        skip_lbl = QLabel(tr("strategy.skip_header"))
        skip_lbl.setStyleSheet(DesignSystem.get_table_header_cell_style())
        skip_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hl.addWidget(skip_lbl, 1)

        self._table_container.addWidget(header)

        # ── Data rows
        for i, path in enumerate(self._files):
            row = QFrame()
            row.setStyleSheet(DesignSystem.get_file_table_row_style(i % 2 == 0))
            row.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            row.customContextMenuRequested.connect(
                lambda pos, idx=i, w=row: self._show_file_context_menu(w, pos, idx)
            )
            rl = QHBoxLayout(row)
            rl.setContentsMargins(12, 3, 12, 3)

            # File name (elided to keep columns aligned)
            name_lbl = ElidedLabel(path.name)
            name_lbl.setStyleSheet(DesignSystem.get_table_row_text_style())
            rl.addWidget(name_lbl, 3)

            # Strategy cells  — each has: [reduction %  👁]
            for pr in presets_in_table:
                cell = self._build_strategy_cell(i, pr)
                rl.addWidget(cell, 2)

            # Skip cell
            skip_selected = self._file_presets.get(i) == _SKIP
            skip_btn = QPushButton(tr("strategy.skip"))
            skip_btn.setFlat(True)
            skip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            skip_btn.setStyleSheet(
                DesignSystem.get_table_cell_btn_style(
                    skip_selected, DesignSystem.COLOR_TEXT_SECONDARY, skip_selected,
                )
            )
            skip_btn.clicked.connect(
                lambda checked=False, idx=i: self._on_cell_clicked(idx, _SKIP)
            )
            rl.addWidget(skip_btn, 1)

            self._table_container.addWidget(row)

    def _build_strategy_cell(self, file_idx: int, preset: PresetName) -> QWidget:
        """Build one table cell: clickable reduction label + eye preview button."""
        gs_blocked = preset_requires_gs(preset) and not self._gs_available
        est = self._estimations.get(file_idx, {}).get(preset)
        selected = self._file_presets.get(file_idx) == preset
        txt = "—"
        color = DesignSystem.COLOR_TEXT_SECONDARY
        bold = False

        if gs_blocked:
            txt = tr("strategy.gs_required")
            color = DesignSystem.COLOR_TEXT_SECONDARY
        elif est and not est.skipped:
            txt = f"{-est.reduction_pct:+.1f}%"
            color = (
                DesignSystem.COLOR_SUCCESS
                if est.reduction_pct > 0
                else DesignSystem.COLOR_DANGER
            )
            bold = True

        cell = QWidget()
        cl = QHBoxLayout(cell)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)
        cl.addStretch()

        # Eye preview button (opens temp PDF in external viewer)
        eye = QToolButton()
        icon_manager.set_button_icon(
            eye, "eye",
            color=DesignSystem.COLOR_TEXT_SECONDARY if not selected else DesignSystem.COLOR_PRIMARY,
            size=12,
        )
        eye.setStyleSheet(DesignSystem.get_preview_icon_btn_style())
        eye.setFixedSize(20, 20)
        eye.setCursor(Qt.CursorShape.PointingHandCursor)
        eye.setToolTip(tr("strategy.preview_tooltip", preset=_preset_label(preset)))

        has_file = est and not est.skipped and est.output_path and est.output_path.exists()
        eye.setEnabled(bool(has_file))
        if has_file:
            eye.clicked.connect(
                lambda checked=False, p=est.output_path: self._open_preview_pdf(p)
            )
        cl.addWidget(eye)

        cl.addSpacing(2)

        # Reduction button (selects strategy)
        btn = QPushButton(txt)
        btn.setFlat(True)
        btn.setStyleSheet(DesignSystem.get_table_cell_btn_style(selected, color, bold))
        btn.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        if gs_blocked:
            btn.setEnabled(False)
            btn.setToolTip(tr("strategy.gs_required_tooltip"))
        else:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(
                lambda checked=False, idx=file_idx, p=preset: self._on_cell_clicked(idx, p)
            )
        cl.addWidget(btn)
        cl.addStretch()
        return cell

    # ── Interactions ─────────────────────────────────────────────────

    @staticmethod
    def _open_preview_pdf(path: Path) -> None:
        """Open a PDF file with the platform's default viewer."""
        from PySide6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _on_apply_all(self, combo: QComboBox, idx: int) -> None:
        if idx == 0:
            return
        preset = combo.itemData(idx)
        if preset is None:
            return
        for i in range(len(self._files)):
            self._file_presets[i] = preset
        
        if preset == PresetName.CUSTOM:
            self._custom_panel.show()
        elif not any(p == PresetName.CUSTOM for p in self._file_presets.values()):
            self._custom_panel.hide()

        self._apply_all_combo.blockSignals(True)
        self._apply_all_combo.setCurrentIndex(0)
        self._apply_all_combo.blockSignals(False)
        self._rebuild_table()

    def _on_cell_clicked(self, idx: int, preset: PresetName | str) -> None:
        if isinstance(preset, PresetName) and preset_requires_gs(preset) and not self._gs_available:
            return
        self._file_presets[idx] = preset
        if preset == PresetName.CUSTOM:
            self._custom_panel.show()
        elif not any(p == PresetName.CUSTOM for p in self._file_presets.values()):
            self._custom_panel.hide()
        self._rebuild_table()

    def _on_custom_estimate(self, opts: OptimizeOptions) -> None:
        self._custom_estimation_worker = CustomEstimationWorker(
            self._files, opts, output_dir=self._est_temp_dir,
        )
        self._custom_estimation_worker.file_done.connect(
            lambda i, r: (
                self._estimations.setdefault(i, {}).update({PresetName.CUSTOM: r}),
                self._rebuild_table(),
            )
        )
        self._custom_estimation_worker.start()

    def _on_custom_optimize(self, opts: OptimizeOptions) -> None:
        ops = [(p, opts) for p in self._files]
        self._run_batch(ops)

    def _on_optimize_clicked(self) -> None:
        ops = []
        for i, path in enumerate(self._files):
            pr = self._file_presets.get(i, _SKIP)
            if pr == _SKIP:
                continue
            if pr == PresetName.CUSTOM:
                opts = self._custom_panel.get_options()
            else:
                opts = preset_by_name(pr)
            ops.append((path, opts))
        if not ops:
            QMessageBox.information(
                self, tr("strategy.nothing_to_optimize_title"),
                tr("strategy.nothing_to_optimize_msg"),
            )
            return
        self._run_batch(ops)

    def _run_batch(self, ops: list[tuple[Path, OptimizeOptions]]) -> None:
        self._inner_stack.setCurrentIndex(2)
        self._batch_worker = BatchOptimizeWorker(ops)
        self._batch_worker.progress.connect(
            lambda info: (
                self._os.setText(
                    tr("strategy.optimising_status",
                       index=info.file_index, total=info.file_total,
                       stage=info.stage, message=info.message)
                ),
                self._op.setValue(int(min(info.percent, 100))),
            )
        )
        self._batch_worker.finished.connect(
            lambda results: self.optimization_complete.emit(self._files, results)
        )
        self._batch_worker.start()

    def _on_cancel_analysis(self) -> None:
        if self._analysis_worker:
            self._analysis_worker.request_cancel()
        if self._estimation_worker:
            self._estimation_worker.request_cancel()
        self._cleanup_temp_dir()
        self.go_back.emit()

    def _on_cancel_optimize(self) -> None:
        if self._batch_worker:
            self._batch_worker.request_cancel()
        self._inner_stack.setCurrentIndex(1)

    # ── Context menu ─────────────────────────────────────────────────

    def _show_file_context_menu(self, widget: QWidget, pos, file_idx: int) -> None:
        """Show right-click context menu for a file row in the strategy table."""
        menu = QMenu(self)
        menu.setStyleSheet(DesignSystem.get_context_menu_style())

        path = self._files[file_idx]
        analysis = self._analyses[file_idx] if file_idx < len(self._analyses) else None

        view_action = menu.addAction(tr("strategy.view_details"))
        view_action.triggered.connect(
            lambda: self._show_details_for_file(path, analysis)
        )

        menu.exec(widget.mapToGlobal(pos))

    def _show_details_for_file(
        self, path: Path, analysis: AnalysisResult | None,
    ) -> None:
        """Open the details dialog for a specific file."""
        from safetool_pdf_desktop.dialogs.details_dialog import DetailsDialog

        if analysis is None:
            try:
                analysis = analyze(path)
            except Exception:
                return
        dlg = DetailsDialog(analysis, parent=self)
        dlg.exec()
