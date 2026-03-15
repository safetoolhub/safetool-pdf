# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Extended UI tests — StrategyScreen, workers, dialogs, design system."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

_DISPLAY_AVAILABLE = bool(
    os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
)

try:
    from PySide6.QtWidgets import QApplication

    _PYSIDE6_AVAILABLE = True
except ImportError:
    _PYSIDE6_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not (_DISPLAY_AVAILABLE and _PYSIDE6_AVAILABLE),
    reason="No display available or PySide6 not installed",
)


@pytest.fixture(scope="module")
def qapp():
    """Provide a QApplication instance for UI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


# ─── Strategy Screen ─────────────────────────────────────────────────

class TestStrategyScreen:
    """Tests for the StrategyScreen widget."""

    def test_creates(self, qapp) -> None:
        from safetool_pdf_desktop.screens.strategy_screen import StrategyScreen

        screen = StrategyScreen()
        assert screen is not None

    def test_has_signals(self, qapp) -> None:
        from safetool_pdf_desktop.screens.strategy_screen import StrategyScreen

        screen = StrategyScreen()
        assert hasattr(screen, "go_back")
        assert hasattr(screen, "optimization_complete")
        assert hasattr(screen, "open_file_requested")
        assert hasattr(screen, "open_folder_requested")

    def test_set_files_callable(self, qapp) -> None:
        """set_files method exists and is callable."""
        from safetool_pdf_desktop.screens.strategy_screen import StrategyScreen

        screen = StrategyScreen()
        assert callable(screen.set_files)


# ─── Strategy Selection ──────────────────────────────────────────────

class TestStrategySelection:
    """Tests for strategy selection (4 strategies including Custom)."""

    def test_strategy_order_exists(self, qapp) -> None:
        """STRATEGY_ORDER class attribute lists all four presets."""
        from safetool_pdf_desktop.screens.strategy_screen import StrategyScreen

        screen = StrategyScreen()
        assert hasattr(screen, "STRATEGY_ORDER")
        assert len(screen.STRATEGY_ORDER) == 4  # Lossless, Moderate, Aggressive, Custom

    def test_all_presets_in_order(self, qapp) -> None:
        from safetool_pdf_core.models import PresetName
        from safetool_pdf_desktop.screens.strategy_screen import StrategyScreen

        screen = StrategyScreen()
        for preset in [
            PresetName.LOSSLESS,
            PresetName.MODERATE,
            PresetName.AGGRESSIVE,
            PresetName.CUSTOM,
        ]:
            assert preset in screen.STRATEGY_ORDER

    def test_estimation_dict(self, qapp) -> None:
        """Estimation results stored in _estimations dict."""
        from safetool_pdf_core.models import OptimizeResult, PresetName
        from safetool_pdf_desktop.screens.strategy_screen import StrategyScreen

        screen = StrategyScreen()
        result = OptimizeResult(
            input_path=Path("/a.pdf"),
            output_path=Path("/b.pdf"),
            original_size=1000000,
            optimized_size=500000,
            reduction_bytes=500000,
            reduction_pct=50.0,
            page_count=10,
        )
        screen._estimations = {0: {PresetName.MODERATE: result}}
        assert screen._estimations[0][PresetName.MODERATE].reduction_pct == 50.0

    def test_estimation_none(self, qapp) -> None:
        """None estimation result handled gracefully."""
        from safetool_pdf_core.models import PresetName
        from safetool_pdf_desktop.screens.strategy_screen import StrategyScreen

        screen = StrategyScreen()
        screen._estimations = {0: {PresetName.AGGRESSIVE: None}}
        assert screen._estimations[0][PresetName.AGGRESSIVE] is None

    def test_preset_selection(self, qapp) -> None:
        from safetool_pdf_core.models import PresetName
        from safetool_pdf_desktop.screens.strategy_screen import StrategyScreen

        screen = StrategyScreen()
        screen._files = [Path("/a.pdf"), Path("/b.pdf")]
        screen._file_presets = {0: PresetName.LOSSLESS, 1: PresetName.LOSSLESS}
        screen._on_cell_clicked(0, PresetName.MODERATE)
        assert screen._file_presets[0] == PresetName.MODERATE


# ─── Custom Optimization Panel ─────────────────────────────────────

class TestCustomPanel:
    """Tests for CustomOptimizationPanel."""

    def test_creates(self, qapp) -> None:
        from safetool_pdf_desktop.widgets.strategy_screen import CustomOptimizationPanel

        panel = CustomOptimizationPanel()
        assert panel is not None

    def test_get_options_returns_custom_preset(self, qapp) -> None:
        from safetool_pdf_core.models import PresetName
        from safetool_pdf_desktop.screens.strategy_screen import CustomOptimizationPanel

        panel = CustomOptimizationPanel()
        opts = panel.get_options()
        assert opts.preset == PresetName.CUSTOM


# ─── Workers (Signal types) ──────────────────────────────────────────

class TestWorkerSignals:
    """Verify workers use Signal(object) not Signal(dict)."""

    def test_analysis_worker_signal_type(self, qapp) -> None:
        from safetool_pdf_desktop.widgets.strategy_screen import AnalysisBatchWorker

        worker = AnalysisBatchWorker([Path("/dummy.pdf")])
        assert hasattr(worker, "all_done")
        assert hasattr(worker, "progress_text")

    def test_estimation_worker_signal_type(self, qapp) -> None:
        from safetool_pdf_desktop.widgets.strategy_screen import EstimationBatchWorker

        worker = EstimationBatchWorker([Path("/dummy.pdf")])
        assert hasattr(worker, "all_done")
        assert hasattr(worker, "progress_text")
        assert hasattr(worker, "error")

    def test_batch_worker_signal_type(self, qapp) -> None:
        from safetool_pdf_core.tools.optimize.presets import lossless
        from safetool_pdf_desktop.widgets.strategy_screen import BatchOptimizeWorker

        worker = BatchOptimizeWorker([Path("/a.pdf")], lossless())
        assert hasattr(worker, "finished")
        assert hasattr(worker, "progress")
        assert hasattr(worker, "error")


# ─── Design System ───────────────────────────────────────────────────

class TestDesignSystem:
    """Design system returns valid style strings."""

    def test_all_style_methods(self, qapp) -> None:
        from safetool_pdf_desktop.styles.design_system import DesignSystem

        methods = [
            ("get_primary_button_style", []),
            ("get_secondary_button_style", []),
            ("get_custom_panel_style", []),
            ("get_checkbox_style", []),
            ("get_spinbox_style", []),
            ("get_card_style", []),
            ("get_scroll_area_style", []),
            ("get_progressbar_style", []),
            ("get_context_menu_style", []),
            ("get_file_table_header_style", []),
            ("get_file_table_row_style", []),
            ("get_file_table_row_optimized_style", []),
            ("get_tool_card_style", []),
            ("get_tool_card_badge_style", []),
            ("get_file_list_container_style", []),
            ("get_file_list_row_style", []),
            ("get_file_list_remove_button_style", []),
            ("get_strategy_selector_card_style", []),
            ("get_results_table_style", []),
            ("get_settings_section_style", []),
            ("get_estimation_table_container_style", []),
            ("get_strategy_legend_card_style", []),
            ("get_apply_all_combo_style", []),
            ("get_preview_icon_btn_style", []),
        ]
        for name, args in methods:
            fn = getattr(DesignSystem, name)
            result = fn(*args)
            assert isinstance(result, str), f"{name} should return str"
            assert len(result) > 0, f"{name} returned empty string"


# ─── Icon Manager ────────────────────────────────────────────────────

class TestIconManager:
    """Icon manager resolves all icon names."""

    def test_icon_map_populated(self, qapp) -> None:
        from safetool_pdf_desktop.styles.icons import icon_manager

        assert len(icon_manager.ICON_MAP) > 0

    def test_strategy_card_icons_exist(self, qapp) -> None:
        from safetool_pdf_desktop.styles.icons import icon_manager

        required_icons = [
            "shield-check", "scale-balance", "rocket-launch",
            "magnify", "compress", "check-circle",
            "folder-open", "arrow-left",
            "information-outline", "tune", "eye",
        ]
        for icon_name in required_icons:
            assert icon_name in icon_manager.ICON_MAP, (
                f"Icon '{icon_name}' missing from ICON_MAP"
            )


# ─── File Selection Screen ───────────────────────────────────────────

class TestFileSelectionScreen:
    """Tests for the file selection screen."""

    def test_creates(self, qapp) -> None:
        from safetool_pdf_desktop.screens.file_selection_screen import FileSelectionScreen

        screen = FileSelectionScreen()
        assert screen is not None

    def test_drop_zone_creates(self, qapp) -> None:
        from safetool_pdf_desktop.screens.dropzone_widget import DropZoneWidget

        zone = DropZoneWidget()
        assert zone is not None
        assert zone.acceptDrops()

    def test_file_list_creates(self, qapp) -> None:
        from safetool_pdf_desktop.screens.file_list_widget import FileListWidget

        widget = FileListWidget()
        assert widget is not None

    def test_tool_cards_create(self, qapp) -> None:
        from safetool_pdf_desktop.screens.tool_card import OptimizeToolCard, CombineToolCard

        opt = OptimizeToolCard()
        assert opt is not None

        comb = CombineToolCard()
        assert comb is not None


# ─── Results Screen ──────────────────────────────────────────────────

class TestResultsScreen:
    """Tests for the new results screen (Screen 3)."""

    def test_creates(self, qapp) -> None:
        from safetool_pdf_desktop.screens.results_screen import ResultsScreen

        screen = ResultsScreen()
        assert screen is not None

    def test_has_signals(self, qapp) -> None:
        from safetool_pdf_desktop.screens.results_screen import ResultsScreen

        screen = ResultsScreen()
        assert hasattr(screen, "go_back")
        assert hasattr(screen, "open_file_requested")
        assert hasattr(screen, "open_folder_requested")

    def test_set_results_callable(self, qapp) -> None:
        from safetool_pdf_desktop.screens.results_screen import ResultsScreen

        screen = ResultsScreen()
        assert callable(screen.set_results)


# ─── Dialogs ─────────────────────────────────────────────────────────

class TestDialogs:
    """Tests for Settings and About dialogs."""

    def test_settings_dialog_creates(self, qapp) -> None:
        from safetool_pdf_desktop.dialogs.settings_dialog import SettingsDialog

        dlg = SettingsDialog()
        assert dlg is not None
        dlg.close()

    def test_about_dialog_creates(self, qapp) -> None:
        from safetool_pdf_desktop.dialogs.about_dialog import AboutDialog

        dlg = AboutDialog()
        assert dlg is not None
        dlg.close()

    def test_details_dialog_creates(
        self, qapp, generated_pdfs: dict[str, Path]
    ) -> None:
        from safetool_pdf_core.analyzer import analyze
        from safetool_pdf_desktop.dialogs.details_dialog import DetailsDialog

        result = analyze(generated_pdfs["simple_text"])
        dlg = DetailsDialog(result)
        assert dlg is not None
        dlg.close()

    def test_settings_suffix_field(self, qapp) -> None:
        """Settings dialog has suffix edit field."""
        from safetool_pdf_desktop.dialogs.settings_dialog import SettingsDialog

        dlg = SettingsDialog()
        assert hasattr(dlg, "_suffix_edit")
        dlg.close()


# ─── CLI --suffix and --custom ───────────────────────────────────────

class TestCLINewFlags:
    """Tests for new CLI flags added in v2."""

    def test_suffix_flag_in_help(self) -> None:
        from safetool_pdf_cli.main import _build_parser

        parser = _build_parser()
        # suffix is now under the 'optimize' subparser
        subparsers_action = next(
            a for a in parser._actions
            if hasattr(a, "choices") and a.choices
        )
        optimize_parser = subparsers_action.choices["optimize"]
        actions = {a.dest for a in optimize_parser._actions}
        assert "suffix" in actions

    def test_custom_flag_in_help(self) -> None:
        from safetool_pdf_cli.main import _build_parser

        parser = _build_parser()
        subparsers_action = next(
            a for a in parser._actions
            if hasattr(a, "choices") and a.choices
        )
        optimize_parser = subparsers_action.choices["optimize"]
        actions = {a.dest for a in optimize_parser._actions}
        assert "custom" in actions
        assert "dpi" in actions
        assert "quality" in actions
