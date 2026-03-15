# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Screen 2: Analysis → Per-file strategy comparison → Optimization → Results.

Redesigned flow:
  - Analyses ALL selected files (not just the first).
  - Estimates savings PER FILE for each of the 3 presets.
  - Displays a professional table with per-file info and reductions.
  - Strategy selector at the top — the user picks one for all files.
  - After optimisation the same table view updates with real results.
"""

from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import Qt, Signal, Slot, QThread
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from safetool_pdf_core.analyzer import analyze
from safetool_pdf_core.models import (
    AnalysisResult,
    OptimizeOptions,
    OptimizeResult,
    PreservationMode,
    PresetName,
    ProgressInfo,
)
from safetool_pdf_core.tools.optimize import preset_by_name
from safetool_pdf_core.tools.optimize import optimize, optimize_batch
from safetool_pdf_desktop.styles.design_system import DesignSystem
from safetool_pdf_desktop.styles.icons import icon_manager


# ── Helpers ──────────────────────────────────────────────────────────

def _format_size(size_bytes: int) -> str:
    """Format bytes to human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


# Preset display metadata
_PRESET_META: dict[PresetName, dict] = {
    PresetName.LOSSLESS: {
        "label": "Lossless",
        "icon": "shield-check",
        "desc": "No quality loss — structure-only optimisation",
        "color": DesignSystem.COLOR_PRIMARY,
    },
    PresetName.MODERATE: {
        "label": "Moderate",
        "icon": "scale-balance",
        "desc": "Good compression with minimal quality impact",
        "color": DesignSystem.COLOR_WARNING,
    },
    PresetName.AGGRESSIVE: {
        "label": "Aggressive",
        "icon": "rocket-launch",
        "desc": "Aggressive compression for smallest file size",
        "color": DesignSystem.COLOR_DANGER,
    },
}


# ======================================================================
# Workers
# ======================================================================


class AnalysisBatchWorker(QThread):
    """Analyse every selected file in background."""

    file_done = Signal(int, object)   # (index, AnalysisResult)
    file_error = Signal(int, str)     # (index, error message)
    all_done = Signal(object)         # list[AnalysisResult | None]
    progress_text = Signal(str)

    def __init__(self, files: list[Path], parent=None) -> None:
        super().__init__(parent)
        self._files = files
        self._cancel = threading.Event()

    def request_cancel(self) -> None:
        self._cancel.set()

    def run(self) -> None:
        results: list[AnalysisResult | None] = []
        total = len(self._files)
        for i, path in enumerate(self._files):
            if self._cancel.is_set():
                return
            self.progress_text.emit(f"Analysing file {i + 1}/{total}: {path.name}")
            try:
                r = analyze(path)
                results.append(r)
                self.file_done.emit(i, r)
            except Exception as exc:
                results.append(None)
                self.file_error.emit(i, str(exc))
        if not self._cancel.is_set():
            self.all_done.emit(results)


class EstimationBatchWorker(QThread):
    """Estimate savings for every file × every preset.

    Emits progress and a final dict keyed *[file_index][PresetName]*.
    """

    progress_text = Signal(str)
    file_preset_done = Signal(int, object, object)  # (index, PresetName, OptimizeResult|None)
    all_done = Signal(object)  # dict[int, dict[PresetName, OptimizeResult|None]]
    error = Signal(str)

    PRESETS = [PresetName.LOSSLESS, PresetName.MODERATE, PresetName.AGGRESSIVE]

    def __init__(self, files: list[Path], parent=None) -> None:
        super().__init__(parent)
        self._files = files
        self._cancel = threading.Event()

    def request_cancel(self) -> None:
        self._cancel.set()

    def run(self) -> None:
        import tempfile, shutil
        all_results: dict[int, dict[PresetName, OptimizeResult | None]] = {}
        total = len(self._files)
        tmp_dir = Path(tempfile.mkdtemp(prefix="safetool_pdf_est_"))

        try:
            for fi, path in enumerate(self._files):
                file_results: dict[PresetName, OptimizeResult | None] = {}
                for preset in self.PRESETS:
                    if self._cancel.is_set():
                        return
                    self.progress_text.emit(
                        f"Estimating {_PRESET_META[preset]['label']} on "
                        f"{path.name} ({fi + 1}/{total})"
                    )
                    try:
                        options = preset_by_name(preset)
                        result = optimize(path, options, output_dir=tmp_dir)
                        file_results[preset] = result
                        self.file_preset_done.emit(fi, preset, result)
                    except Exception:
                        file_results[preset] = None
                        self.file_preset_done.emit(fi, preset, None)
                all_results[fi] = file_results

            if not self._cancel.is_set():
                self.all_done.emit(all_results)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


class BatchOptimizeWorker(QThread):
    """Optimise a list of files with a given preset/options."""

    progress = Signal(object)   # ProgressInfo
    finished = Signal(object)   # list[OptimizeResult]
    error = Signal(str)

    def __init__(
        self,
        files: list[Path],
        options: OptimizeOptions,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._files = files
        self._options = options
        self._cancel = threading.Event()

    def request_cancel(self) -> None:
        self._cancel.set()

    def run(self) -> None:
        try:
            results = optimize_batch(
                self._files,
                self._options,
                progress_cb=lambda info: self.progress.emit(info),
                cancel=self._cancel,
            )
            self.finished.emit(results)
        except Exception as exc:
            self.error.emit(str(exc))


# ======================================================================
# Custom Optimization Panel
# ======================================================================


class CustomOptimizationPanel(QFrame):
    """Expandable panel for custom optimization settings."""

    optimize_clicked = Signal(OptimizeOptions)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        self.setStyleSheet(DesignSystem.get_custom_panel_style())
        layout = QVBoxLayout(self)
        layout.setSpacing(DesignSystem.SPACE_12)

        title = QLabel("Custom Optimization")
        title.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_MD}px;"
            f"font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};"
            f"color: {DesignSystem.COLOR_TEXT};"
            f"border: none; background: transparent;"
        )
        layout.addWidget(title)

        desc = QLabel("Fine-tune compression parameters.")
        desc.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f"border: none; background: transparent;"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # --- Image settings ---
        img_header = QLabel("Image Compression")
        img_header.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};"
            f"color: {DesignSystem.COLOR_TEXT};"
            f"border: none; background: transparent;"
            f"margin-top: {DesignSystem.SPACE_8}px;"
        )
        layout.addWidget(img_header)

        self._enable_images = QCheckBox("Enable lossy image compression")
        self._enable_images.setStyleSheet(DesignSystem.get_checkbox_style())
        self._enable_images.toggled.connect(self._on_images_toggled)
        layout.addWidget(self._enable_images)

        img_row = QHBoxLayout()
        img_row.setSpacing(DesignSystem.SPACE_16)

        dpi_label = QLabel("Target DPI:")
        dpi_label.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"color: {DesignSystem.COLOR_TEXT};"
            f"border: none; background: transparent;"
        )
        img_row.addWidget(dpi_label)
        self._dpi_spin = QSpinBox()
        self._dpi_spin.setRange(72, 600)
        self._dpi_spin.setValue(150)
        self._dpi_spin.setStyleSheet(DesignSystem.get_spinbox_style())
        self._dpi_spin.setEnabled(False)
        img_row.addWidget(self._dpi_spin)

        quality_label = QLabel("JPEG Quality:")
        quality_label.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"color: {DesignSystem.COLOR_TEXT};"
            f"border: none; background: transparent;"
        )
        img_row.addWidget(quality_label)
        self._quality_spin = QSpinBox()
        self._quality_spin.setRange(10, 100)
        self._quality_spin.setValue(80)
        self._quality_spin.setStyleSheet(DesignSystem.get_spinbox_style())
        self._quality_spin.setEnabled(False)
        img_row.addWidget(self._quality_spin)

        img_row.addStretch()
        layout.addLayout(img_row)

        # --- Ghostscript settings ---
        gs_header = QLabel("Ghostscript")
        gs_header.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};"
            f"color: {DesignSystem.COLOR_TEXT};"
            f"border: none; background: transparent;"
            f"margin-top: {DesignSystem.SPACE_8}px;"
        )
        layout.addWidget(gs_header)

        self._enable_gs = QCheckBox("Enable Ghostscript processing")
        self._enable_gs.setStyleSheet(DesignSystem.get_checkbox_style())
        self._enable_gs.toggled.connect(self._on_gs_toggled)
        layout.addWidget(self._enable_gs)

        gs_row = QHBoxLayout()
        gs_row.setSpacing(DesignSystem.SPACE_16)
        self._font_subset = QCheckBox("Font subsetting")
        self._font_subset.setStyleSheet(DesignSystem.get_checkbox_style())
        self._font_subset.setEnabled(False)
        gs_row.addWidget(self._font_subset)

        self._full_rewrite = QCheckBox("Full PDF rewrite")
        self._full_rewrite.setStyleSheet(DesignSystem.get_checkbox_style())
        self._full_rewrite.setEnabled(False)
        gs_row.addWidget(self._full_rewrite)
        gs_row.addStretch()
        layout.addLayout(gs_row)

        # --- Cleanup ---
        cleanup_header = QLabel("Cleanup")
        cleanup_header.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};"
            f"color: {DesignSystem.COLOR_TEXT};"
            f"border: none; background: transparent;"
            f"margin-top: {DesignSystem.SPACE_8}px;"
        )
        layout.addWidget(cleanup_header)

        self._remove_metadata = QCheckBox("Remove metadata")
        self._remove_metadata.setStyleSheet(DesignSystem.get_checkbox_style())
        layout.addWidget(self._remove_metadata)

        self._flatten_forms = QCheckBox("Flatten forms")
        self._flatten_forms.setStyleSheet(DesignSystem.get_checkbox_style())
        layout.addWidget(self._flatten_forms)

        self._remove_js = QCheckBox("Remove JavaScript")
        self._remove_js.setStyleSheet(DesignSystem.get_checkbox_style())
        layout.addWidget(self._remove_js)

        # Optimize button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._optimize_btn = QPushButton("  Optimize with Custom Settings")
        icon_manager.set_button_icon(
            self._optimize_btn, "tune",
            color=DesignSystem.COLOR_PRIMARY_TEXT, size=18,
        )
        self._optimize_btn.setStyleSheet(DesignSystem.get_primary_button_style())
        self._optimize_btn.clicked.connect(self._on_optimize)
        btn_row.addWidget(self._optimize_btn)
        layout.addLayout(btn_row)

    def _on_images_toggled(self, checked: bool) -> None:
        self._dpi_spin.setEnabled(checked)
        self._quality_spin.setEnabled(checked)

    def _on_gs_toggled(self, checked: bool) -> None:
        self._font_subset.setEnabled(checked)
        self._full_rewrite.setEnabled(checked)

    def _on_optimize(self) -> None:
        self.optimize_clicked.emit(self.get_options())

    def get_options(self) -> OptimizeOptions:
        from safetool_pdf_core.models import (
            CleanupOptions,
            GhostscriptOptions,
            LosslessOptions,
            LossyImageOptions,
        )

        return OptimizeOptions(
            preset=PresetName.CUSTOM,
            preservation=PreservationMode.PRESERVE,
            lossless=LosslessOptions(),
            lossy_images=LossyImageOptions(
                enabled=self._enable_images.isChecked(),
                target_dpi=self._dpi_spin.value(),
                jpeg_quality=self._quality_spin.value(),
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


# ======================================================================
# Strategy Screen (Screen 2) — Redesigned
# ======================================================================


class StrategyScreen(QWidget):
    """Screen 2: per-file analysis → strategy comparison table → optimise.

    Pages (QStackedWidget):
        0 — Analysing / estimating   (progress spinner)
        1 — Comparison table          (file×strategy matrix)
        2 — Optimising                (progress bar)
    """

    go_back = Signal()
    optimize_requested = Signal(PresetName)
    open_file_requested = Signal(Path)
    open_folder_requested = Signal(Path)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._files: list[Path] = []
        self._analyses: list[AnalysisResult | None] = []
        self._estimations: dict[int, dict[PresetName, OptimizeResult | None]] = {}
        self._batch_results: list[OptimizeResult] = []
        self._selected_preset: PresetName = PresetName.LOSSLESS
        self._optimized = False

        # Workers
        self._analysis_worker: AnalysisBatchWorker | None = None
        self._estimation_worker: EstimationBatchWorker | None = None
        self._batch_worker: BatchOptimizeWorker | None = None

        self._build_ui()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._inner_stack = QStackedWidget()
        layout.addWidget(self._inner_stack)

        self._inner_stack.addWidget(self._build_analyzing_page())   # 0
        self._inner_stack.addWidget(self._build_comparison_page())  # 1
        self._inner_stack.addWidget(self._build_optimizing_page())  # 2

    # ---- Page 0: Analysing / Estimating ----

    def _build_analyzing_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(DesignSystem.SPACE_16)

        layout.addStretch()

        icon_label = QLabel()
        icon_manager.set_label_icon(
            icon_label, "magnify", color=DesignSystem.COLOR_PRIMARY, size=48,
        )
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        self._analyzing_title = QLabel("Analysing files…")
        self._analyzing_title.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_LG}px;"
            f"font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};"
            f"color: {DesignSystem.COLOR_TEXT};"
        )
        self._analyzing_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._analyzing_title)

        self._analyzing_status = QLabel("Reading PDF structure…")
        self._analyzing_status.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"color: {DesignSystem.COLOR_TEXT_SECONDARY};"
        )
        self._analyzing_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._analyzing_status)

        self._analyzing_progress = QProgressBar()
        self._analyzing_progress.setRange(0, 0)
        self._analyzing_progress.setStyleSheet(DesignSystem.get_progressbar_style())
        self._analyzing_progress.setMaximumWidth(400)
        layout.addWidget(self._analyzing_progress, 0, Qt.AlignmentFlag.AlignCenter)

        layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        cancel_btn.clicked.connect(self._on_cancel_analysis)
        layout.addWidget(cancel_btn, 0, Qt.AlignmentFlag.AlignCenter)

        layout.addSpacerItem(QSpacerItem(0, 40))
        return page

    # ---- Page 1: Comparison table ----

    def _build_comparison_page(self) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(DesignSystem.get_scroll_area_style())

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(DesignSystem.SPACE_16)
        layout.setContentsMargins(
            DesignSystem.SPACE_16, DesignSystem.SPACE_12,
            DesignSystem.SPACE_16, DesignSystem.SPACE_12,
        )

        # ── Top bar: Back + file summary ─────────────────────────────
        top_bar = QHBoxLayout()
        top_bar.setSpacing(DesignSystem.SPACE_12)

        back_btn = QPushButton("  Back")
        icon_manager.set_button_icon(back_btn, "arrow-left", size=16)
        back_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        back_btn.clicked.connect(self.go_back.emit)
        top_bar.addWidget(back_btn)

        self._file_info_label = QLabel("")
        self._file_info_label.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_BASE}px;"
            f"font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};"
            f"color: {DesignSystem.COLOR_TEXT};"
        )
        top_bar.addWidget(self._file_info_label, 1)

        layout.addLayout(top_bar)

        # ── Section title ────────────────────────────────────────────
        self._section_title = QLabel("Choose an Optimization Strategy")
        self._section_title.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_XL}px;"
            f"font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
            f"color: {DesignSystem.COLOR_TEXT};"
        )
        layout.addWidget(self._section_title)

        self._section_desc = QLabel(
            "Estimated savings shown for each file and strategy. "
            "Select a strategy, then click Optimise."
        )
        self._section_desc.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_BASE}px;"
            f"color: {DesignSystem.COLOR_TEXT_SECONDARY};"
        )
        self._section_desc.setWordWrap(True)
        layout.addWidget(self._section_desc)

        # ── Strategy selector tabs ───────────────────────────────────
        tabs_row = QHBoxLayout()
        tabs_row.setSpacing(DesignSystem.SPACE_12)

        self._strategy_buttons: dict[PresetName, QPushButton] = {}
        for preset in [PresetName.LOSSLESS, PresetName.MODERATE, PresetName.AGGRESSIVE]:
            meta = _PRESET_META[preset]
            btn = QPushButton(f"  {meta['label']}")
            icon_manager.set_button_icon(btn, meta["icon"], size=18)
            btn.setStyleSheet(
                DesignSystem.get_strategy_tab_style(preset == PresetName.LOSSLESS)
            )
            btn.clicked.connect(lambda checked=False, p=preset: self._on_tab_clicked(p))
            self._strategy_buttons[preset] = btn
            tabs_row.addWidget(btn)

        tabs_row.addStretch()

        # Optimise button (right side of tab bar)
        self._optimize_btn = QPushButton("  Optimise All")
        icon_manager.set_button_icon(
            self._optimize_btn, "rocket-launch",
            color=DesignSystem.COLOR_PRIMARY_TEXT, size=18,
        )
        self._optimize_btn.setStyleSheet(DesignSystem.get_primary_button_style())
        self._optimize_btn.clicked.connect(self._on_optimize_clicked)
        tabs_row.addWidget(self._optimize_btn)

        layout.addLayout(tabs_row)

        # ── Strategy description ─────────────────────────────────────
        self._strategy_desc_label = QLabel(_PRESET_META[PresetName.LOSSLESS]["desc"])
        self._strategy_desc_label.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f"font-style: italic;"
        )
        layout.addWidget(self._strategy_desc_label)

        # ── File table ───────────────────────────────────────────────
        self._table_container = QVBoxLayout()
        self._table_container.setSpacing(0)
        layout.addLayout(self._table_container)

        # ── Custom optimization (expandable) ─────────────────────────
        self._custom_toggle = QPushButton("  Advanced: Custom Optimization…")
        icon_manager.set_button_icon(self._custom_toggle, "tune", size=16)
        self._custom_toggle.setStyleSheet(DesignSystem.get_expandable_section_style())
        self._custom_toggle.setCheckable(True)
        self._custom_toggle.toggled.connect(self._on_custom_toggled)
        layout.addWidget(self._custom_toggle)

        self._custom_panel = CustomOptimizationPanel()
        self._custom_panel.setVisible(False)
        self._custom_panel.optimize_clicked.connect(self._on_custom_optimize)
        layout.addWidget(self._custom_panel)

        # ── Bottom action row (shown after optimisation) ─────────────
        self._bottom_actions = QWidget()
        self._bottom_actions.setVisible(False)
        btn_row = QHBoxLayout(self._bottom_actions)
        btn_row.setContentsMargins(0, DesignSystem.SPACE_12, 0, 0)
        btn_row.setSpacing(DesignSystem.SPACE_12)

        self._open_folder_btn = QPushButton("  Open Folder")
        icon_manager.set_button_icon(self._open_folder_btn, "folder-open", size=16)
        self._open_folder_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        self._open_folder_btn.clicked.connect(self._on_open_folder)
        btn_row.addWidget(self._open_folder_btn)

        btn_row.addStretch()

        new_btn = QPushButton("  Optimise More Files")
        icon_manager.set_button_icon(new_btn, "plus", size=16)
        new_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        new_btn.clicked.connect(self.go_back.emit)
        btn_row.addWidget(new_btn)

        layout.addWidget(self._bottom_actions)

        layout.addStretch()

        scroll.setWidget(content)
        page_layout.addWidget(scroll)
        return page

    # ---- Page 2: Optimising ----

    def _build_optimizing_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(DesignSystem.SPACE_16)

        layout.addStretch()

        icon_label = QLabel()
        icon_manager.set_label_icon(
            icon_label, "compress", color=DesignSystem.COLOR_PRIMARY, size=48,
        )
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        self._opt_title = QLabel("Optimising…")
        self._opt_title.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_LG}px;"
            f"font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};"
            f"color: {DesignSystem.COLOR_TEXT};"
        )
        self._opt_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._opt_title)

        self._opt_status = QLabel("")
        self._opt_status.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"color: {DesignSystem.COLOR_TEXT_SECONDARY};"
        )
        self._opt_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._opt_status)

        self._opt_progress = QProgressBar()
        self._opt_progress.setRange(0, 100)
        self._opt_progress.setStyleSheet(DesignSystem.get_progressbar_style())
        self._opt_progress.setMaximumWidth(400)
        layout.addWidget(self._opt_progress, 0, Qt.AlignmentFlag.AlignCenter)

        layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        cancel_btn.clicked.connect(self._on_cancel_optimize)
        layout.addWidget(cancel_btn, 0, Qt.AlignmentFlag.AlignCenter)

        layout.addSpacerItem(QSpacerItem(0, 40))
        return page

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_files(self, files: list[Path]) -> None:
        """Called by MainWindow when files are selected."""
        self._files = files
        self._analyses = []
        self._estimations = {}
        self._batch_results = []
        self._optimized = False
        self._selected_preset = PresetName.LOSSLESS
        self._bottom_actions.setVisible(False)

        # Reset tab styling
        for p, btn in self._strategy_buttons.items():
            btn.setStyleSheet(
                DesignSystem.get_strategy_tab_style(p == PresetName.LOSSLESS)
            )
        self._strategy_desc_label.setText(_PRESET_META[PresetName.LOSSLESS]["desc"])

        self._inner_stack.setCurrentIndex(0)

        if files:
            self._start_analysis_batch()

    # ------------------------------------------------------------------
    # Analysis + Estimation flow
    # ------------------------------------------------------------------

    def _start_analysis_batch(self) -> None:
        n = len(self._files)
        self._analyzing_title.setText(
            f"Analysing {n} file{'s' if n > 1 else ''}…"
        )
        self._analyzing_status.setText("Reading PDF structures…")

        self._analysis_worker = AnalysisBatchWorker(self._files)
        self._analysis_worker.progress_text.connect(
            lambda msg: self._analyzing_status.setText(msg)
        )
        self._analysis_worker.all_done.connect(self._on_analysis_batch_done)
        self._analysis_worker.start()

    @Slot(object)
    def _on_analysis_batch_done(self, results: list) -> None:
        self._analyses = results

        # Move to estimation phase
        self._analyzing_title.setText("Estimating savings…")
        self._analyzing_status.setText("Running strategies on each file…")

        self._estimation_worker = EstimationBatchWorker(self._files)
        self._estimation_worker.progress_text.connect(
            lambda msg: self._analyzing_status.setText(msg)
        )
        self._estimation_worker.all_done.connect(self._on_estimation_batch_done)
        self._estimation_worker.error.connect(self._on_analysis_error)
        self._estimation_worker.start()

    @Slot(object)
    def _on_estimation_batch_done(self, results: dict) -> None:
        self._estimations = results
        self._populate_file_info()
        self._rebuild_table()
        self._inner_stack.setCurrentIndex(1)

    @Slot(str)
    def _on_analysis_error(self, error_msg: str) -> None:
        QMessageBox.warning(self, "Analysis Error", error_msg)
        self.go_back.emit()

    def _on_cancel_analysis(self) -> None:
        if self._analysis_worker and self._analysis_worker.isRunning():
            self._analysis_worker.request_cancel()
        if self._estimation_worker and self._estimation_worker.isRunning():
            self._estimation_worker.request_cancel()
        self.go_back.emit()

    # ------------------------------------------------------------------
    # File info & summary
    # ------------------------------------------------------------------

    def _populate_file_info(self) -> None:
        n = len(self._files)
        total_size = sum(f.stat().st_size for f in self._files if f.is_file())

        if n == 1:
            a = self._analyses[0] if self._analyses else None
            if a:
                self._file_info_label.setText(
                    f"{a.path.name}  —  {a.page_count} pages  •  "
                    f"{_format_size(a.file_size)}"
                )
            else:
                self._file_info_label.setText(self._files[0].name)
        else:
            self._file_info_label.setText(
                f"{n} files selected  •  {_format_size(total_size)} total"
            )

    # ------------------------------------------------------------------
    # Table building
    # ------------------------------------------------------------------

    def _clear_layout(self, layout) -> None:
        """Recursively remove all widgets / sub-layouts."""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def _rebuild_table(self) -> None:
        """(Re-)build the per-file table for the currently selected preset."""
        self._clear_layout(self._table_container)

        preset = self._selected_preset

        # ── Header row ───────────────────────────────────────────────
        header = QFrame()
        header.setStyleSheet(DesignSystem.get_file_table_header_style())
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(DesignSystem.SPACE_8)

        col_defs = self._column_defs()
        for label_text, stretch, min_w, align in col_defs:
            lbl = QLabel(label_text)
            lbl.setStyleSheet(
                f"font-size: {DesignSystem.FONT_SIZE_XS}px;"
                f"font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};"
                f"color: {DesignSystem.COLOR_TEXT_SECONDARY};"
                f"text-transform: uppercase; letter-spacing: 0.5px;"
                f"border: none; background: transparent;"
            )
            lbl.setAlignment(align)
            lbl.setMinimumWidth(min_w)
            h_layout.addWidget(lbl, stretch)

        self._table_container.addWidget(header)

        # ── Data rows ────────────────────────────────────────────────
        for i, path in enumerate(self._files):
            analysis = self._analyses[i] if i < len(self._analyses) else None
            estimation = (
                self._estimations.get(i, {}).get(preset)
                if not self._optimized
                else None
            )
            opt_result = (
                self._batch_results[i]
                if self._optimized and i < len(self._batch_results)
                else None
            )

            row = self._build_file_row(i, path, analysis, estimation, opt_result)
            self._table_container.addWidget(row)

        # ── Summary row ──────────────────────────────────────────────
        summary = self._build_summary_row()
        if summary:
            self._table_container.addWidget(summary)

    def _column_defs(self) -> list[tuple[str, int, int, Qt.AlignmentFlag]]:
        """Column definitions: (label, stretch, min_width, alignment)."""
        base = [
            ("File", 3, 200, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            ("Size", 1, 80, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
            ("Pages", 0, 55, Qt.AlignmentFlag.AlignCenter),
        ]
        if self._optimized:
            base += [
                ("New Size", 1, 80, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
                ("Saved", 1, 70, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
                ("", 0, 60, Qt.AlignmentFlag.AlignCenter),
            ]
        else:
            base += [
                ("Est. Size", 1, 80, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
                ("Est. Saving", 1, 80, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
            ]
        return base

    def _build_file_row(
        self,
        index: int,
        path: Path,
        analysis: AnalysisResult | None,
        estimation: OptimizeResult | None,
        opt_result: OptimizeResult | None,
    ) -> QFrame:
        even = index % 2 == 0

        row = QFrame()
        if self._optimized and opt_result and not opt_result.skipped:
            row.setStyleSheet(DesignSystem.get_file_table_row_optimized_style(even))
        else:
            row.setStyleSheet(DesignSystem.get_file_table_row_style(even))

        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(DesignSystem.SPACE_8)

        mono = (
            f"font-family: {DesignSystem.FONT_FAMILY_MONO};"
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"border: none; background: transparent;"
        )
        base_style = (
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"border: none; background: transparent;"
        )

        # ── Filename ─────────────────────────────────────────────────
        name_lbl = QLabel(path.name)
        name_lbl.setStyleSheet(
            f"{base_style}"
            f"font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};"
            f"color: {DesignSystem.COLOR_TEXT};"
        )
        name_lbl.setMinimumWidth(200)
        name_lbl.setToolTip(str(path))
        h.addWidget(name_lbl, 3)

        # ── Original size ────────────────────────────────────────────
        orig_size = analysis.file_size if analysis else (path.stat().st_size if path.is_file() else 0)
        size_lbl = QLabel(_format_size(orig_size))
        size_lbl.setStyleSheet(f"{mono} color: {DesignSystem.COLOR_TEXT};")
        size_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        size_lbl.setMinimumWidth(80)
        h.addWidget(size_lbl, 1)

        # ── Pages ────────────────────────────────────────────────────
        pages = analysis.page_count if analysis else "–"
        pages_lbl = QLabel(str(pages))
        pages_lbl.setStyleSheet(f"{mono} color: {DesignSystem.COLOR_TEXT_SECONDARY};")
        pages_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pages_lbl.setMinimumWidth(55)
        h.addWidget(pages_lbl, 0)

        if self._optimized:
            # ── Actual new size ───────────────────────────────────────
            if opt_result and not opt_result.skipped:
                new_lbl = QLabel(_format_size(opt_result.optimized_size))
                new_lbl.setStyleSheet(f"{mono} color: {DesignSystem.COLOR_SUCCESS};")
            elif opt_result and opt_result.skipped:
                new_lbl = QLabel("Skipped")
                new_lbl.setStyleSheet(f"{base_style} color: {DesignSystem.COLOR_DANGER};")
                new_lbl.setToolTip(opt_result.skipped_reason or "")
            else:
                new_lbl = QLabel("–")
                new_lbl.setStyleSheet(f"{mono} color: {DesignSystem.COLOR_TEXT_SECONDARY};")
            new_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            new_lbl.setMinimumWidth(80)
            h.addWidget(new_lbl, 1)

            # ── Actual saved % ────────────────────────────────────────
            if opt_result and not opt_result.skipped and opt_result.reduction_pct > 0:
                pct_color = (
                    DesignSystem.COLOR_SUCCESS if opt_result.reduction_pct >= 10
                    else DesignSystem.COLOR_TEXT_SECONDARY
                )
                saved_lbl = QLabel(f"-{opt_result.reduction_pct:.1f}%")
                saved_lbl.setStyleSheet(
                    f"{mono} color: {pct_color};"
                    f"font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
                )
            else:
                saved_lbl = QLabel("–")
                saved_lbl.setStyleSheet(f"{mono} color: {DesignSystem.COLOR_TEXT_SECONDARY};")
            saved_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            saved_lbl.setMinimumWidth(70)
            h.addWidget(saved_lbl, 1)

            # ── Open button ───────────────────────────────────────────
            if opt_result and not opt_result.skipped:
                open_btn = QPushButton("Open")
                open_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
                open_btn.setFixedWidth(60)
                open_btn.clicked.connect(
                    lambda _=False, p=opt_result.output_path: self.open_file_requested.emit(p)
                )
                h.addWidget(open_btn, 0)
            else:
                spacer = QLabel("")
                spacer.setMinimumWidth(60)
                h.addWidget(spacer, 0)
        else:
            # ── Estimated new size ────────────────────────────────────
            if estimation and not estimation.skipped:
                est_lbl = QLabel(_format_size(estimation.optimized_size))
                est_lbl.setStyleSheet(f"{mono} color: {DesignSystem.COLOR_PRIMARY};")
            else:
                est_lbl = QLabel("–")
                est_lbl.setStyleSheet(f"{mono} color: {DesignSystem.COLOR_TEXT_SECONDARY};")
            est_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            est_lbl.setMinimumWidth(80)
            h.addWidget(est_lbl, 1)

            # ── Estimated saving % ────────────────────────────────────
            if estimation and not estimation.skipped and estimation.reduction_pct > 0:
                pct_color = (
                    DesignSystem.COLOR_SUCCESS if estimation.reduction_pct >= 10
                    else DesignSystem.COLOR_TEXT_SECONDARY
                )
                est_pct = QLabel(f"-{estimation.reduction_pct:.1f}%")
                est_pct.setStyleSheet(
                    f"{mono} color: {pct_color};"
                    f"font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
                )
            else:
                est_pct = QLabel("–")
                est_pct.setStyleSheet(f"{mono} color: {DesignSystem.COLOR_TEXT_SECONDARY};")
            est_pct.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            est_pct.setMinimumWidth(80)
            h.addWidget(est_pct, 1)

        return row

    def _build_summary_row(self) -> QFrame | None:
        """Build a totals / summary row at the bottom of the table."""
        if not self._files:
            return None

        summary = QFrame()
        summary.setStyleSheet(
            f"QFrame {{"
            f"  background-color: {DesignSystem.COLOR_BACKGROUND};"
            f"  border: 2px solid {DesignSystem.COLOR_BORDER};"
            f"  border-radius: 0 0 {DesignSystem.RADIUS_SM}px {DesignSystem.RADIUS_SM}px;"
            f"  padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_12}px;"
            f"}}"
        )
        h = QHBoxLayout(summary)
        h.setContentsMargins(0, 0, 0, 0)
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
        total_lbl = QLabel(f"TOTAL ({len(self._files)} files)")
        total_lbl.setStyleSheet(f"{bold} color: {DesignSystem.COLOR_TEXT};")
        total_lbl.setMinimumWidth(200)
        h.addWidget(total_lbl, 3)

        # Total original size
        total_orig = sum(
            (self._analyses[i].file_size if i < len(self._analyses) and self._analyses[i] else
             self._files[i].stat().st_size if self._files[i].is_file() else 0)
            for i in range(len(self._files))
        )
        orig_lbl = QLabel(_format_size(total_orig))
        orig_lbl.setStyleSheet(f"{mono} color: {DesignSystem.COLOR_TEXT};")
        orig_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        orig_lbl.setMinimumWidth(80)
        h.addWidget(orig_lbl, 1)

        # Pages total
        total_pages = sum(
            self._analyses[i].page_count
            for i in range(len(self._files))
            if i < len(self._analyses) and self._analyses[i]
        )
        pages_lbl = QLabel(str(total_pages))
        pages_lbl.setStyleSheet(f"{mono} color: {DesignSystem.COLOR_TEXT_SECONDARY};")
        pages_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pages_lbl.setMinimumWidth(55)
        h.addWidget(pages_lbl, 0)

        if self._optimized:
            ok = [r for r in self._batch_results if not r.skipped]
            total_opt = sum(r.optimized_size for r in ok)
            total_orig_ok = sum(r.original_size for r in ok)

            opt_lbl = QLabel(_format_size(total_opt))
            opt_lbl.setStyleSheet(f"{mono} color: {DesignSystem.COLOR_SUCCESS};")
            opt_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            opt_lbl.setMinimumWidth(80)
            h.addWidget(opt_lbl, 1)

            avg_pct = ((total_orig_ok - total_opt) / total_orig_ok * 100) if total_orig_ok else 0
            pct_lbl = QLabel(f"-{avg_pct:.1f}%")
            pct_lbl.setStyleSheet(f"{mono} color: {DesignSystem.COLOR_SUCCESS};")
            pct_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            pct_lbl.setMinimumWidth(70)
            h.addWidget(pct_lbl, 1)

            spacer = QLabel("")
            spacer.setMinimumWidth(60)
            h.addWidget(spacer, 0)
        else:
            preset = self._selected_preset
            est_sizes = []
            for i in range(len(self._files)):
                est = self._estimations.get(i, {}).get(preset)
                if est and not est.skipped:
                    est_sizes.append((est.original_size, est.optimized_size))

            if est_sizes:
                total_est = sum(o for _, o in est_sizes)
                total_est_orig = sum(o for o, _ in est_sizes)
                avg_pct = ((total_est_orig - total_est) / total_est_orig * 100) if total_est_orig else 0

                est_lbl = QLabel(_format_size(total_est))
                est_lbl.setStyleSheet(f"{mono} color: {DesignSystem.COLOR_PRIMARY};")
                est_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                est_lbl.setMinimumWidth(80)
                h.addWidget(est_lbl, 1)

                pct_lbl = QLabel(f"-{avg_pct:.1f}%")
                pct_color = DesignSystem.COLOR_SUCCESS if avg_pct >= 10 else DesignSystem.COLOR_TEXT_SECONDARY
                pct_lbl.setStyleSheet(f"{mono} color: {pct_color};")
                pct_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                pct_lbl.setMinimumWidth(80)
                h.addWidget(pct_lbl, 1)
            else:
                for _ in range(2):
                    dash = QLabel("–")
                    dash.setStyleSheet(f"{mono} color: {DesignSystem.COLOR_TEXT_SECONDARY};")
                    dash.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    dash.setMinimumWidth(80)
                    h.addWidget(dash, 1)

        return summary

    # ------------------------------------------------------------------
    # Strategy tab interaction
    # ------------------------------------------------------------------

    def _on_tab_clicked(self, preset: PresetName) -> None:
        if self._optimized:
            return  # Don't allow switching after optimisation
        self._selected_preset = preset
        for p, btn in self._strategy_buttons.items():
            btn.setStyleSheet(DesignSystem.get_strategy_tab_style(p == preset))
        self._strategy_desc_label.setText(_PRESET_META[preset]["desc"])
        self._rebuild_table()

    def _on_custom_toggled(self, checked: bool) -> None:
        self._custom_panel.setVisible(checked)

    @Slot(OptimizeOptions)
    def _on_custom_optimize(self, options: OptimizeOptions) -> None:
        self._run_batch(options)

    def _on_optimize_clicked(self) -> None:
        preset = self._selected_preset
        self.optimize_requested.emit(preset)
        self._run_batch(preset_by_name(preset))

    # ------------------------------------------------------------------
    # Batch optimization
    # ------------------------------------------------------------------

    def _run_batch(self, options: OptimizeOptions) -> None:
        if not self._files:
            return

        n = len(self._files)
        self._inner_stack.setCurrentIndex(2)
        self._opt_progress.setValue(0)
        self._opt_title.setText(f"Optimising {n} file{'s' if n > 1 else ''}…")
        self._opt_status.setText("Starting…")

        self._batch_worker = BatchOptimizeWorker(self._files, options)
        self._batch_worker.progress.connect(self._on_opt_progress)
        self._batch_worker.finished.connect(self._on_batch_done)
        self._batch_worker.error.connect(self._on_opt_error)
        self._batch_worker.start()

    @Slot(object)
    def _on_opt_progress(self, info: ProgressInfo) -> None:
        total = info.file_total or 1
        file_pct = info.percent / total
        base_pct = ((info.file_index - 1) / total) * 100
        overall = base_pct + file_pct
        self._opt_progress.setValue(int(min(overall, 100)))
        if total > 1:
            self._opt_status.setText(
                f"File {info.file_index}/{total}: {info.stage} — {info.message}"
            )
        else:
            self._opt_status.setText(f"{info.stage}: {info.message}")

    def _on_cancel_optimize(self) -> None:
        if self._batch_worker:
            self._batch_worker.request_cancel()

    @Slot(object)
    def _on_batch_done(self, results: list) -> None:
        self._batch_results = results
        self._optimized = True

        # Update UI to show results in the SAME table view
        ok = [r for r in results if not r.skipped]
        n_ok = len(ok)
        n_skip = len(results) - n_ok

        if n_skip == 0:
            self._section_title.setText("Optimisation Complete!")
            self._section_title.setStyleSheet(
                f"font-size: {DesignSystem.FONT_SIZE_XL}px;"
                f"font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
                f"color: {DesignSystem.COLOR_SUCCESS};"
            )
        else:
            self._section_title.setText(f"Done — {n_skip} file(s) skipped")
            self._section_title.setStyleSheet(
                f"font-size: {DesignSystem.FONT_SIZE_XL}px;"
                f"font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
                f"color: {DesignSystem.COLOR_WARNING};"
            )

        # Summary description
        if ok:
            total_orig = sum(r.original_size for r in ok)
            total_opt = sum(r.optimized_size for r in ok)
            saved = total_orig - total_opt
            avg_pct = (saved / total_orig * 100) if total_orig else 0
            self._section_desc.setText(
                f"Saved {_format_size(saved)} overall ({avg_pct:.1f}% average reduction). "
                f"{n_ok}/{len(results)} files optimised successfully."
            )
        else:
            self._section_desc.setText("No files were optimised.")

        # Disable strategy switching and hide optimize button
        self._optimize_btn.setVisible(False)
        self._custom_toggle.setVisible(False)
        self._custom_panel.setVisible(False)
        self._bottom_actions.setVisible(True)

        # Rebuild table with actual results
        self._rebuild_table()
        self._inner_stack.setCurrentIndex(1)

    @Slot(str)
    def _on_opt_error(self, error_msg: str) -> None:
        QMessageBox.critical(self, "Optimisation Error", error_msg)
        self._inner_stack.setCurrentIndex(1)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_open_folder(self) -> None:
        ok = [r for r in self._batch_results if not r.skipped]
        if ok:
            self.open_folder_requested.emit(ok[0].output_path)

    # ------------------------------------------------------------------
    # Context menu
    # ------------------------------------------------------------------

    def contextMenuEvent(self, event) -> None:  # noqa: N802
        if not self._analyses:
            return

        menu = QMenu(self)
        menu.setStyleSheet(DesignSystem.get_context_menu_style())

        if self._analyses and any(self._analyses):
            first_valid = next((a for a in self._analyses if a), None)
            if first_valid:
                view_action = menu.addAction("View PDF Details")
                view_action.triggered.connect(
                    lambda: self._show_details_dialog(first_valid)
                )

        if self._batch_results:
            ok = [r for r in self._batch_results if not r.skipped]
            if ok:
                menu.addSeparator()
                if len(ok) == 1:
                    open_action = menu.addAction("Open Optimised File")
                    open_action.triggered.connect(
                        lambda: self.open_file_requested.emit(ok[0].output_path)
                    )
                folder_action = menu.addAction("Open Containing Folder")
                folder_action.triggered.connect(self._on_open_folder)

        menu.exec(event.globalPos())

    def _show_details_dialog(self, analysis: AnalysisResult) -> None:
        from safetool_pdf_desktop.widgets.details_dialog import DetailsDialog

        dlg = DetailsDialog(analysis, parent=self)
        dlg.exec()
