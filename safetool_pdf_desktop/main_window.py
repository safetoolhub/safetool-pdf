# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Main application window — 3-screen UX, no menu bar, header with branding."""

from __future__ import annotations

import logging
import subprocess
import platform
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QSize, Slot
from PySide6.QtGui import QCloseEvent, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from safetool_pdf_core.constants import APP_NAME, VERSION
from safetool_pdf_core.models import (
    AnalysisResult,
    OptimizeOptions,
    OptimizeResult,
    PreservationMode,
    PresetName,
    ProgressInfo,
    ToolName,
    ToolResult,
)
from safetool_pdf_core.tools.optimize import preset_by_name
from safetool_pdf_desktop.styles.design_system import DesignSystem
from safetool_pdf_desktop.styles.icons import icon_manager
from i18n import tr

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """SafeTool PDF main application window.

    Multi-screen UX flow:
        Screen 0: File selection (drop zone + file list + tool cards).
        Screen 1: Strategy comparison & optimization (Optimize tool).
        Screen 2: Optimization results.
        Screen 3: Simple tool screen (Numbering / Metadata / Merge).
        Screen 4: Unlock / permissions management.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} {VERSION}")
        self.setMinimumSize(
            DesignSystem.WINDOW_MIN_WIDTH,
            DesignSystem.WINDOW_MIN_HEIGHT,
        )

        # State
        self._files: list[Path] = []
        self._current_analysis: AnalysisResult | None = None
        self._selected_preset: PresetName | None = None

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Build the main layout: header + stacked screens."""
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(
            DesignSystem.SPACE_16,
            DesignSystem.SPACE_12,
            DesignSystem.SPACE_16,
            DesignSystem.SPACE_12,
        )
        root_layout.setSpacing(DesignSystem.SPACE_12)

        # Header
        header = self._create_header()
        root_layout.addWidget(header)

        # Stacked widget for three screens
        self._stack = QStackedWidget()
        root_layout.addWidget(self._stack, 1)

        # Screen 1: File selection
        from safetool_pdf_desktop.screens.file_selection_screen import FileSelectionScreen

        self._file_screen = FileSelectionScreen()
        self._file_screen.files_selected.connect(self._on_files_selected)
        self._file_screen.tool_selected.connect(self._on_tool_selected)
        self._stack.addWidget(self._file_screen)  # index 0

        # Screen 2: Strategy comparison & optimization
        from safetool_pdf_desktop.screens.strategy_screen import StrategyScreen

        self._strategy_screen = StrategyScreen()
        self._strategy_screen.go_back.connect(self._on_go_back)
        self._strategy_screen.optimization_complete.connect(self._on_optimization_complete)
        self._strategy_screen.open_file_requested.connect(self._open_file)
        self._strategy_screen.open_folder_requested.connect(self._open_folder)
        self._stack.addWidget(self._strategy_screen)  # index 1

        # Screen 3: Results (optimization + tool results, unified)
        from safetool_pdf_desktop.screens.results_screen import ResultsScreen

        self._results_screen = ResultsScreen()
        self._results_screen.go_back.connect(self._on_back_to_start)
        self._results_screen.use_another_tool.connect(self._on_use_another_tool)
        self._results_screen.open_file_requested.connect(self._open_file)
        self._results_screen.open_folder_requested.connect(self._open_folder)
        self._stack.addWidget(self._results_screen)  # index 2

        # Screen 4: Simple tool (numbering, metadata, merge)
        from safetool_pdf_desktop.screens.simple_tool_screen import SimpleToolScreen

        self._simple_tool_screen = SimpleToolScreen()
        self._simple_tool_screen.go_back.connect(self._on_go_back)
        self._simple_tool_screen.tool_complete.connect(self._on_tool_complete)
        self._stack.addWidget(self._simple_tool_screen)  # index 3

        # Screen 5: Unlock / permissions management
        from safetool_pdf_desktop.screens.unlock_screen import UnlockScreen

        self._unlock_screen = UnlockScreen()
        self._unlock_screen.go_back.connect(self._on_go_back)
        self._unlock_screen.tool_complete.connect(self._on_tool_complete)
        self._stack.addWidget(self._unlock_screen)  # index 4

        # Screen 6: Split PDF
        from safetool_pdf_desktop.screens.split_screen import SplitScreen

        self._split_screen = SplitScreen()
        self._split_screen.go_back.connect(self._on_go_back)
        self._split_screen.tool_complete.connect(self._on_tool_complete)
        self._stack.addWidget(self._split_screen)  # index 5

    def _create_header(self) -> QFrame:
        """Create the branded header bar: Title | 'by safetoolhub' | settings + about."""
        card = QFrame()
        card.setObjectName("headerCard")
        card.setStyleSheet(DesignSystem.get_header_style())

        layout = QHBoxLayout(card)
        layout.setSpacing(DesignSystem.SPACE_12)
        layout.setContentsMargins(
            DesignSystem.SPACE_16, 0, DesignSystem.SPACE_16, 0
        )

        # App icon
        icon_container = QFrame()
        icon_container.setFixedSize(48, 48)
        icon_container.setStyleSheet(DesignSystem.get_header_icon_container_style())
        icon_layout = QHBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        app_icon = QLabel()
        # Load application icon from assets
        icon_path = Path(__file__).parent.parent / "assets" / "icon.png"
        if icon_path.exists():
            pixmap = QPixmap(str(icon_path))
            scaled_pixmap = pixmap.scaled(
                36, 36,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            app_icon.setPixmap(scaled_pixmap)
        else:
            # Fallback to QtAwesome icon if file not found
            icon_manager.set_label_icon(
                app_icon, 'file-pdf',
                color=DesignSystem.COLOR_PRIMARY, size=36,
            )
        icon_layout.addWidget(app_icon)
        layout.addWidget(icon_container)

        # Title + "by safetoolhub"
        text_container = QWidget()
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        title_row = QWidget()
        title_row_layout = QHBoxLayout(title_row)
        title_row_layout.setContentsMargins(0, 0, 0, 0)
        title_row_layout.setSpacing(DesignSystem.SPACE_12)
        title_row_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        title_label = QLabel(APP_NAME)
        title_label.setStyleSheet(DesignSystem.get_header_title_style())
        title_row_layout.addWidget(title_label)

        by_label = QLabel(tr("header.by_safetoolhub"))
        by_label.setStyleSheet(DesignSystem.get_header_brand_label_style())
        by_label.setAlignment(Qt.AlignmentFlag.AlignBottom)
        title_row_layout.addWidget(by_label)
        title_row_layout.addStretch()

        text_layout.addWidget(title_row)
        layout.addWidget(text_container)

        # Spacer
        layout.addStretch()

        # Settings button
        btn_settings = QToolButton()
        btn_settings.setAutoRaise(True)
        btn_settings.setToolTip(tr("header.settings"))
        icon_manager.set_button_icon(
            btn_settings, 'cog',
            color=DesignSystem.COLOR_TEXT_SECONDARY, size=20,
        )
        btn_settings.setIconSize(QSize(20, 20))
        btn_settings.clicked.connect(self._show_settings)
        btn_settings.setStyleSheet(DesignSystem.get_icon_button_style())
        layout.addWidget(btn_settings)

        # About button
        btn_about = QToolButton()
        btn_about.setAutoRaise(True)
        btn_about.setToolTip(tr("header.about"))
        icon_manager.set_button_icon(
            btn_about, 'information-outline',
            color=DesignSystem.COLOR_TEXT_SECONDARY, size=20,
        )
        btn_about.setIconSize(QSize(20, 20))
        btn_about.clicked.connect(self._show_about)
        btn_about.setStyleSheet(DesignSystem.get_icon_button_style())
        layout.addWidget(btn_about)

        return card

    # ------------------------------------------------------------------
    # Slots — navigation
    # ------------------------------------------------------------------

    @Slot(list)
    def _on_files_selected(self, files: list[Path]) -> None:
        """Files selected on Screen 1 → move to Screen 2 (Optimize)."""
        self._files = files
        self._strategy_screen.set_files(files)
        self._stack.setCurrentIndex(1)

    @Slot(object, list)
    def _on_tool_selected(self, tool: ToolName, files: list[Path]) -> None:
        """A tool card was clicked — route to the correct screen."""
        logger.info("Tool selected: %s  (%d file%s)", tool.value, len(files), "s" if len(files) != 1 else "")
        for i, f in enumerate(files, 1):
            logger.info("  [%d] %s", i, f.resolve())
        self._files = files
        if tool == ToolName.OPTIMIZE:
            self._strategy_screen.set_files(files)
            self._stack.setCurrentIndex(1)
        elif tool in (ToolName.MERGE, ToolName.NUMBER, ToolName.STRIP_METADATA):
            self._simple_tool_screen.set_tool(tool, files)
            self._stack.setCurrentIndex(3)
        elif tool == ToolName.UNLOCK:
            self._unlock_screen.set_files(files)
            self._stack.setCurrentIndex(4)
        elif tool == ToolName.SPLIT:
            self._split_screen.set_files(files)
            self._stack.setCurrentIndex(5)

    @Slot()
    def _on_go_back(self) -> None:
        """Go back to file selection."""
        self._stack.setCurrentIndex(0)

    @Slot()
    def _on_back_to_start(self) -> None:
        """Go back to file selection from results — reset the file list."""
        self._file_screen.reset()
        self._stack.setCurrentIndex(0)

    @Slot(list, list)
    def _on_optimization_complete(
        self, files: list[Path], results: list[OptimizeResult],
    ) -> None:
        """Optimization finished → show results on Screen 3."""
        self._results_screen.set_results(files, results)
        self._stack.setCurrentIndex(2)

    @Slot(object, list, list)
    def _on_tool_complete(
        self, tool: ToolName, files: list[Path], results: list[ToolResult],
    ) -> None:
        """A non-optimization tool finished → show results screen."""
        self._results_screen.set_tool_results(tool, files, results)
        self._stack.setCurrentIndex(2)

    @Slot(list)
    def _on_use_another_tool(self, files: list[Path]) -> None:
        """User wants to use another tool on the same files."""
        self._files = files
        self._file_screen.set_files(files)
        self._stack.setCurrentIndex(0)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _open_file(self, path: Path) -> None:
        """Open file with default system viewer."""
        if platform.system() == "Darwin":
            subprocess.Popen(["open", str(path)])
        elif platform.system() == "Windows":
            subprocess.Popen(["start", "", str(path)], shell=True)
        else:
            subprocess.Popen(["xdg-open", str(path)])

    def _open_folder(self, path: Path) -> None:
        """Open folder containing the file."""
        folder = path.parent
        if platform.system() == "Darwin":
            subprocess.Popen(["open", str(folder)])
        elif platform.system() == "Windows":
            subprocess.Popen(["explorer", str(folder)])
        else:
            subprocess.Popen(["xdg-open", str(folder)])

    def _show_settings(self) -> None:
        """Show settings dialog."""
        from safetool_pdf_desktop.dialogs.settings_dialog import SettingsDialog

        dlg = SettingsDialog(self)
        dlg.exec()

    def _show_about(self) -> None:
        """Show about dialog."""
        from safetool_pdf_desktop.dialogs.about_dialog import AboutDialog

        dlg = AboutDialog(self)
        dlg.exec()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Clean up resources before closing the application."""
        logger.info("Application closing - cleaning up resources")
        
        # Close any open dialogs first
        for widget in self.findChildren(QWidget):
            if isinstance(widget, QWidget) and widget.isWindow() and widget != self:
                widget.close()
        
        # Cancel and wait for all workers in strategy screen
        if hasattr(self, '_strategy_screen'):
            for worker_attr in ['_analysis_worker', '_estimation_worker', 
                               '_custom_estimation_worker', '_batch_worker']:
                if hasattr(self._strategy_screen, worker_attr):
                    worker = getattr(self._strategy_screen, worker_attr, None)
                    if worker and worker.isRunning():
                        logger.debug(f"Stopping {worker_attr}")
                        worker.request_cancel()
                        worker.wait(1000)  # Wait up to 1 second
                        if worker.isRunning():
                            worker.terminate()
                            worker.wait()
        
        # Cancel and wait for worker in simple tool screen
        if hasattr(self, '_simple_tool_screen'):
            if hasattr(self._simple_tool_screen, '_worker'):
                worker = self._simple_tool_screen._worker
                if worker and worker.isRunning():
                    logger.debug("Stopping simple tool worker")
                    worker.request_cancel()
                    worker.wait(1000)
                    if worker.isRunning():
                        worker.terminate()
                        worker.wait()

        # Cancel and wait for worker in unlock screen
        if hasattr(self, '_unlock_screen'):
            if hasattr(self._unlock_screen, '_worker'):
                worker = self._unlock_screen._worker
                if worker and worker.isRunning():
                    logger.debug("Stopping unlock worker")
                    worker.request_cancel()
                    worker.wait(1000)
                    if worker.isRunning():
                        worker.terminate()
                        worker.wait()
        
        # Force cleanup of any remaining PyMuPDF resources
        try:
            import fitz
            # This helps ensure all PyMuPDF documents are properly closed
            import gc
            gc.collect()
        except Exception as e:
            logger.debug(f"Error during PyMuPDF cleanup: {e}")
        
        logger.info("Cleanup complete")
        event.accept()
