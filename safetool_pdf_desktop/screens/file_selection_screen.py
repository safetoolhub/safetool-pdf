# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Screen 1: File selection — drop zone + browse + file list + tool cards."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from safetool_pdf_core.models import ToolName
from safetool_pdf_desktop.screens.dropzone_widget import DropZoneWidget
from safetool_pdf_desktop.screens.file_list_widget import FileListWidget
from safetool_pdf_desktop.screens.tool_card import (
    CombineToolCard,
    MetadataToolCard,
    NumberingToolCard,
    OptimizeToolCard,
    SplitToolCard,
    UnlockToolCard,
)
from safetool_pdf_desktop.styles.design_system import DesignSystem
from safetool_pdf_desktop.styles.icons import icon_manager
from i18n import tr


class FileSelectionScreen(QWidget):
    """Screen 1 — File selection + tool cards.

    Layout:
        - Drop zone (tall, centred icon/text)
        - Browse button centred below the drop zone
        - Scrollable file list with per-file remove
        - Separator "Choose a Tool"
        - 5 tool cards in responsive grid

    Signals:
        files_selected(list[Path]) — emitted when Optimize card is clicked (legacy).
        tool_selected(object, list) — emitted when any tool card is clicked.
            First arg is ToolName, second is list[Path].
    """

    files_selected = Signal(list)  # list[Path] — kept for backward compat
    tool_selected = Signal(object, list)  # (ToolName, list[Path])

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(DesignSystem.SPACE_24)
        layout.setContentsMargins(
            DesignSystem.SPACE_16, DesignSystem.SPACE_12,
            DesignSystem.SPACE_16, DesignSystem.SPACE_12,
        )

        # --- STEP 1: FILE SELECTION ---
        self._step_1_container = QFrame()
        self._step_1_container.setObjectName("filesSection")
        self._step_1_container.setStyleSheet(DesignSystem.get_card_style())
        
        step_1_layout = QVBoxLayout(self._step_1_container)
        step_1_layout.setSpacing(DesignSystem.SPACE_16)
        
        # Section Header
        header_layout = QHBoxLayout()
        self._step_1_label = QLabel(tr("file_selection.step_1_title"))
        self._step_1_label.setStyleSheet(DesignSystem.get_header_text_style())
        header_layout.addWidget(self._step_1_label)
        
        header_layout.addStretch()
        
        # Add Files Button (Visible only when list is not empty)
        self._add_files_btn = QPushButton(tr("file_selection.add_files"))
        self._add_files_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_files_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        self._add_files_btn.setMinimumHeight(32)
        icon_manager.set_button_icon(self._add_files_btn, 'plus', color=DesignSystem.COLOR_TEXT, size=16)
        self._add_files_btn.clicked.connect(self._browse_files)
        self._add_files_btn.setVisible(False)
        header_layout.addWidget(self._add_files_btn)
        
        step_1_layout.addLayout(header_layout)

        # Drop zone (Big)
        self._drop_zone = DropZoneWidget()
        self._drop_zone.files_dropped.connect(self._on_files_dropped)
        self._drop_zone.browse_requested.connect(self._browse_files)
        step_1_layout.addWidget(self._drop_zone)

        # File list
        self._file_list = FileListWidget()
        self._file_list.files_changed.connect(self._on_file_list_changed)
        self._file_list.view_details_requested.connect(self._on_view_details)
        self._file_list.setVisible(False)
        step_1_layout.addWidget(self._file_list)

        # Supported formats hint
        self._formats_label = QLabel(tr("file_selection.formats_hint"))
        self._formats_label.setStyleSheet(DesignSystem.get_formats_hint_style())
        self._formats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        step_1_layout.addWidget(self._formats_label)
        
        layout.addWidget(self._step_1_container, 0)

        # --- STEP 2: TOOL SELECTION ---
        self._step_2_container = QWidget()
        step_2_layout = QVBoxLayout(self._step_2_container)
        step_2_layout.setContentsMargins(0, 0, 0, 0)
        step_2_layout.setSpacing(DesignSystem.SPACE_16)

        # Step 2 Header
        self._step_2_label = QLabel(tr("file_selection.step_2_title"))
        self._step_2_label.setStyleSheet(DesignSystem.get_header_text_style())
        step_2_layout.addWidget(self._step_2_label)

        # Tool cards container — responsive grid
        self._cards_container = QWidget()
        self._cards_grid = QGridLayout(self._cards_container)
        self._cards_grid.setContentsMargins(0, 0, 0, 0)
        self._cards_grid.setSpacing(DesignSystem.SPACE_16)

        self._optimize_card = OptimizeToolCard()
        self._optimize_card.clicked.connect(self._on_optimize_clicked)

        self._combine_card = CombineToolCard()
        self._combine_card.clicked.connect(self._on_combine_clicked)

        self._numbering_card = NumberingToolCard()
        self._numbering_card.clicked.connect(self._on_numbering_clicked)

        self._metadata_card = MetadataToolCard()
        self._metadata_card.clicked.connect(self._on_metadata_clicked)

        self._unlock_card = UnlockToolCard()
        self._unlock_card.clicked.connect(self._on_unlock_clicked)

        self._split_card = SplitToolCard()
        self._split_card.clicked.connect(self._on_split_clicked)

        self._all_cards = [
            self._optimize_card,
            self._combine_card,
            self._split_card,
            self._numbering_card,
            self._unlock_card,
            self._metadata_card,
        ]

        self._last_cols = 0
        self._relayout_cards()

        step_2_layout.addWidget(self._cards_container)
        layout.addWidget(self._step_2_container, 0)
        
        # Initial State: Step 2 hidden but retaining space
        sp = self._step_2_container.sizePolicy()
        sp.setRetainSizeWhenHidden(True)
        self._step_2_container.setSizePolicy(sp)
        self._step_2_container.setVisible(False)
        
        layout.addStretch()

    def resizeEvent(self, event) -> None:  # noqa: N802
        """Update the card grid for the current width."""
        super().resizeEvent(event)
        self._relayout_cards()

    def _relayout_cards(self) -> None:
        """Arrange tool cards in a responsive grid: 4 cols / 3 cols / 2 cols / 1 col."""
        w = self.width()
        if w >= 1100:
            cols = 4
        elif w >= 800:
            cols = 3
        elif w >= 550:
            cols = 2
        else:
            cols = 1

        if cols == self._last_cols:
            return
        self._last_cols = cols

        # Remove all cards from the grid (don't delete them)
        while self._cards_grid.count():
            self._cards_grid.takeAt(0)

        max_w = 320 if cols > 1 else 600
        for i, card in enumerate(self._all_cards):
            card.setMaximumWidth(max_w)
            self._cards_grid.addWidget(card, i // cols, i % cols)


    # ── Slots ──

    def _on_files_dropped(self, files: list[Path]) -> None:
        """Accumulate dropped files into the list."""
        self._file_list.add_files(files)

    def _browse_files(self) -> None:
        """Open a file dialog and add selected PDFs."""
        paths, _ = QFileDialog.getOpenFileNames(
            self, tr("file_selection.dialog_title"), "", tr("file_selection.dialog_filter"),
        )
        if paths:
            self._file_list.add_files([Path(p) for p in paths])

    def _on_file_list_changed(self, files: list[Path]) -> None:
        """Update UI states based on file count."""
        has_files = len(files) > 0
        
        # Toggle between empty state (Drop zone) and populated state (List)
        self._drop_zone.setVisible(not has_files)
        self._formats_label.setVisible(not has_files)
        
        self._file_list.setVisible(has_files)
        self._add_files_btn.setVisible(has_files)
        
        # Show/Hide Step 2 (Tool selection)
        self._step_2_container.setVisible(has_files)
        
        # Update all cards enabled state
        for card in self._all_cards:
            card.set_enabled(has_files)

    def _on_optimize_clicked(self) -> None:
        """Emit tool_selected when the Optimize card is clicked."""
        files = self._file_list.get_files()
        if files:
            self.tool_selected.emit(ToolName.OPTIMIZE, files)

    def _on_combine_clicked(self) -> None:
        """Emit tool_selected for Merge."""
        files = self._file_list.get_files()
        if not files:
            return
        if len(files) < 2:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                tr("merge_screen.title"),
                tr("merge_screen.min_files_required"),
            )
            return
        self.tool_selected.emit(ToolName.MERGE, files)

    def _on_numbering_clicked(self) -> None:
        """Emit tool_selected for Numbering."""
        files = self._file_list.get_files()
        if files:
            self.tool_selected.emit(ToolName.NUMBER, files)

    def _on_metadata_clicked(self) -> None:
        """Emit tool_selected for Strip Metadata."""
        files = self._file_list.get_files()
        if files:
            self.tool_selected.emit(ToolName.STRIP_METADATA, files)

    def _on_unlock_clicked(self) -> None:
        """Emit tool_selected for Unlock."""
        files = self._file_list.get_files()
        if files:
            self.tool_selected.emit(ToolName.UNLOCK, files)

    def _on_split_clicked(self) -> None:
        """Emit tool_selected for Split."""
        files = self._file_list.get_files()
        if files:
            self.tool_selected.emit(ToolName.SPLIT, files)

    def _on_view_details(self, path: Path) -> None:
        """Show the details dialog for a file (via right-click context menu)."""
        from safetool_pdf_core.analyzer import analyze
        from safetool_pdf_desktop.dialogs.details_dialog import DetailsDialog

        try:
            analysis = analyze(path)
        except Exception:
            return
        dlg = DetailsDialog(analysis, parent=self)
        dlg.exec()

    def set_files(self, files: list[Path]) -> None:
        """Load *files* into the list (used when returning from results)."""
        self._file_list.set_files(files)

    def reset(self) -> None:
        """Clear all files — called when returning from results."""
        self._file_list.set_files([])
