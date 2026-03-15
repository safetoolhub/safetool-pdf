# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Reusable screen for simple tools — Numbering, Metadata removal, Merge.

Redesigned to show a file table with predicted output names, context menus
(view details, rename output), magnify icons, and tool-specific config panels.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, Signal, Slot, QMimeData, QPoint
from PySide6.QtGui import QPainter, QFontMetrics, QDrag, QCursor, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from safetool_pdf_core.models import ProgressInfo, ToolName, ToolResult
from safetool_pdf_core.naming import output_path_for
from safetool_pdf_desktop.styles.design_system import DesignSystem
from safetool_pdf_desktop.styles.icons import icon_manager
from i18n import tr

_logger = logging.getLogger(__name__)


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


_TOOL_META: dict[ToolName, dict] = {
    ToolName.NUMBER: {
        "icon": "numeric",
        "color": DesignSystem.COLOR_PRIMARY,
        "title_key": "simple_tool.numbering_title",
        "subtitle_key": "simple_tool.numbering_subtitle",
    },
    ToolName.STRIP_METADATA: {
        "icon": "shield-remove",
        "color": DesignSystem.COLOR_WARNING,
        "title_key": "simple_tool.metadata_title",
        "subtitle_key": "simple_tool.metadata_subtitle",
    },
    ToolName.MERGE: {
        "icon": "file-multiple",
        "color": DesignSystem.COLOR_PRIMARY,
        "title_key": "merge_screen.title",
        "subtitle_key": "merge_screen.subtitle",
    },
}


class ElidedLabel(QLabel):
    """A QLabel that automatically elides its text with '...' if it overflows."""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setMinimumWidth(1)
        self._original_text = text

    def setText(self, text: str) -> None:
        """Override setText to store the original text."""
        self._original_text = text
        super().setText(text)

    def paintEvent(self, event) -> None:
        # If using RichText, let Qt handle it with elision
        if self.textFormat() == Qt.TextFormat.RichText:
            painter = QPainter(self)
            # For rich text, we need to strip HTML for elision measurement
            import re
            plain_text = re.sub('<[^<]+?>', '', self._original_text)
            metrics = QFontMetrics(self.font())
            
            if metrics.horizontalAdvance(plain_text) > self.width():
                # Text is too long, need to elide
                elided_plain = metrics.elidedText(plain_text, Qt.TextElideMode.ElideRight, self.width())
                # Apply the same HTML styling to elided text
                # Extract the color from original HTML
                color_match = re.search(r'color:\s*([^;"]+)', self._original_text)
                if color_match:
                    color = color_match.group(1)
                    painter.drawText(self.rect(), self.alignment(), elided_plain)
                else:
                    painter.drawText(self.rect(), self.alignment(), elided_plain)
            else:
                # Text fits, render as HTML
                super().paintEvent(event)
                return
            painter.end()
        else:
            # Plain text elision
            painter = QPainter(self)
            metrics = QFontMetrics(self.font())
            elided_text = metrics.elidedText(
                self.text(), Qt.TextElideMode.ElideRight, self.width(),
            )
            painter.drawText(self.rect(), self.alignment(), elided_text)
            painter.end()





class DraggableFileRow(QFrame):
    """A file row that can be dragged and dropped to reorder."""
    
    rowMoved = Signal(int, int)  # Emits (from_index, to_index)
    
    def __init__(self, index: int, is_draggable: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._index = index
        self._is_draggable = is_draggable
        self._drag_start_pos = None
        self._original_style = ""
        # Only accept drops if this row is draggable
        self.setAcceptDrops(is_draggable)
        
    def set_index(self, index: int) -> None:
        """Update the row index."""
        self._index = index
        
    def get_index(self) -> int:
        """Get the current row index."""
        return self._index
        
    def mousePressEvent(self, event) -> None:
        """Store the position where drag started."""
        if event.button() == Qt.MouseButton.LeftButton and self._is_draggable:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event) -> None:
        """Start drag operation if mouse moved enough."""
        if not self._is_draggable:
            return
            
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if self._drag_start_pos is None:
            return
            
        # Check if we've moved enough to start a drag
        if (event.pos() - self._drag_start_pos).manhattanLength() < 10:
            return
            
        # Store original style
        self._original_style = self.styleSheet()
        
        # Create drag with visual feedback
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(str(self._index))
        drag.setMimeData(mime_data)
        
        # Create a pixmap of the row for drag image
        pixmap = self.grab()
        
        # Make it semi-transparent and add shadow effect
        from PySide6.QtGui import QPainter
        transparent_pixmap = QPixmap(pixmap.size())
        transparent_pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(transparent_pixmap)
        painter.setOpacity(0.7)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()
        
        drag.setPixmap(transparent_pixmap)
        drag.setHotSpot(event.pos())
        
        # Make the original row semi-transparent while dragging
        self.setStyleSheet(self._original_style + f"background-color: rgba(37, 99, 235, 0.1); opacity: 0.5;")
        
        # Change cursor during drag
        self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
        
        # Execute drag
        result = drag.exec(Qt.DropAction.MoveAction)
        
        # Restore original style and cursor
        self.setStyleSheet(self._original_style)
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        
    def dragEnterEvent(self, event) -> None:
        """Accept drag events from other rows."""
        if not self._is_draggable:
            event.ignore()
            return
            
        if event.mimeData().hasText():
            from_index = int(event.mimeData().text())
            # Don't highlight if dragging over itself
            if from_index != self._index:
                event.acceptProposedAction()
                # Add a top border to show where the row will be inserted
                self.setStyleSheet(self.styleSheet() + f"border-top: 3px solid {DesignSystem.COLOR_PRIMARY};")
            
    def dragLeaveEvent(self, event) -> None:
        """Remove highlight when drag leaves."""
        if not self._is_draggable:
            return
        # Reset to original style (will be set by parent)
        self.setStyleSheet(DesignSystem.get_file_table_row_style(self._index % 2 == 0))
        
    def dropEvent(self, event) -> None:
        """Handle drop event."""
        if not self._is_draggable:
            event.ignore()
            return
            
        if event.mimeData().hasText():
            from_index = int(event.mimeData().text())
            to_index = self._index
            
            if from_index != to_index:
                self.rowMoved.emit(from_index, to_index)
                
            event.acceptProposedAction()
            
        # Reset style
        self.setStyleSheet(DesignSystem.get_file_table_row_style(self._index % 2 == 0))


class SimpleToolScreen(QWidget):
    """Screen for simple PDF tools (Numbering, Metadata, Merge).

    Adapts its config panel based on the current ``ToolName``.
    Shows a file table with predicted output names (editable via context menu).

    Signals
    -------
    go_back : emitted when the user clicks back.
    tool_complete(ToolName, list[Path], list[ToolResult]) : tool finished.
    """

    go_back = Signal()
    tool_complete = Signal(object, list, list)  # (ToolName, files, results)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tool: ToolName | None = None
        self._files: list[Path] = []
        self._output_names: dict[int, str] = {}  # idx → custom output name
        self._output_filename = "merged"  # For merge tool
        self._worker = None
        self._file_encryption_status: dict[int, bool] = {}  # idx → is_encrypted
        self._build_ui()

    # ------------------------------------------------------------------
    # UI
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

        # ── Top bar: Back + Title + file info
        top = QHBoxLayout()
        self._back_btn = QPushButton(tr("strategy.back"))
        icon_manager.set_button_icon(self._back_btn, "arrow-left", size=16)
        self._back_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        self._back_btn.clicked.connect(self._on_back)
        top.addWidget(self._back_btn)
        top.addSpacing(16)

        self._tool_icon = QLabel()
        top.addWidget(self._tool_icon)
        top.addSpacing(8)

        self._title_label = QLabel()
        self._title_label.setStyleSheet(DesignSystem.get_strategy_header_text_style())
        top.addWidget(self._title_label)
        top.addStretch()

        self._file_info_label = QLabel()
        self._file_info_label.setStyleSheet(DesignSystem.get_strategy_info_text_style())
        top.addWidget(self._file_info_label)
        lay.addLayout(top)

        # ── Subtitle / description
        self._subtitle_label = QLabel()
        self._subtitle_label.setWordWrap(True)
        self._subtitle_label.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"color: {DesignSystem.COLOR_TEXT_SECONDARY};"
        )
        lay.addWidget(self._subtitle_label)

        # ── Config panel (tool-dependent) ──
        self._config_container = QFrame()
        self._config_container.setStyleSheet(DesignSystem.get_custom_panel_style())
        self._config_layout = QVBoxLayout(self._config_container)
        self._config_layout.setContentsMargins(16, 12, 16, 12)
        self._config_layout.setSpacing(DesignSystem.SPACE_12)

        # Numbering: start number
        self._number_row = QWidget()
        nr_layout = QHBoxLayout(self._number_row)
        nr_layout.setContentsMargins(0, 0, 0, 0)
        nr_icon = QLabel()
        icon_manager.set_label_icon(
            nr_icon, "numeric", color=DesignSystem.COLOR_PRIMARY, size=16,
        )
        nr_layout.addWidget(nr_icon)
        nr_layout.addSpacing(8)
        nr_label = QLabel(tr("simple_tool.numbering_start_label"))
        nr_label.setStyleSheet(DesignSystem.get_custom_section_header_style())
        nr_layout.addWidget(nr_label)
        nr_layout.addSpacing(12)
        self._start_spin = QSpinBox()
        self._start_spin.setRange(1, 99999)
        self._start_spin.setValue(1)
        self._start_spin.setFixedWidth(100)
        self._start_spin.setStyleSheet(DesignSystem.get_spinbox_style())
        self._start_spin.valueChanged.connect(self._on_start_number_changed)
        nr_layout.addWidget(self._start_spin)
        nr_layout.addStretch()
        self._config_layout.addWidget(self._number_row)

        # Merge: output filename field
        self._merge_row = QWidget()
        merge_layout = QVBoxLayout(self._merge_row)
        merge_layout.setContentsMargins(0, 0, 0, 0)
        merge_layout.setSpacing(8)
        
        # Title row with icon
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        merge_icon = QLabel()
        icon_manager.set_label_icon(
            merge_icon, "file-multiple", color=DesignSystem.COLOR_PRIMARY, size=16,
        )
        title_row.addWidget(merge_icon)
        merge_title = QLabel(tr("merge_screen.output_filename_label"))
        merge_title.setStyleSheet(DesignSystem.get_custom_section_header_style())
        title_row.addWidget(merge_title)
        title_row.addStretch()
        merge_layout.addLayout(title_row)
        
        # Input field row
        input_row = QHBoxLayout()
        input_row.setSpacing(12)
        
        self._output_filename_input = QLineEdit()
        self._output_filename_input.setText(self._output_filename)
        self._output_filename_input.setPlaceholderText(tr("merge_screen.output_filename_placeholder"))
        self._output_filename_input.setStyleSheet(
            DesignSystem.get_line_edit_style().replace(
                DesignSystem.COLOR_TEXT, DesignSystem.COLOR_PRIMARY,
            )
        )
        self._output_filename_input.setMinimumWidth(300)
        self._output_filename_input.textChanged.connect(self._on_filename_changed)
        input_row.addWidget(self._output_filename_input)
        
        pdf_ext = QLabel(".pdf")
        pdf_ext.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_MD}px;"
            f"color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f"font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
            f"background: transparent;"
            f"border: none;"
        )
        input_row.addWidget(pdf_ext)
        input_row.addStretch()
        
        merge_layout.addLayout(input_row)
        self._config_layout.addWidget(self._merge_row)

        lay.addWidget(self._config_container)

        # ── File table ──
        table_frame = QFrame()
        table_frame.setStyleSheet(DesignSystem.get_estimation_table_container_style())
        tf_lay = QVBoxLayout(table_frame)
        tf_lay.setContentsMargins(0, 0, 0, 0)
        self._table_container = QVBoxLayout()
        self._table_container.setSpacing(0)
        tf_lay.addLayout(self._table_container)
        lay.addWidget(table_frame)

        # ── Execute button ──
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._execute_btn = QPushButton(f"  {tr('simple_tool.btn_execute')}")
        self._execute_btn.setMinimumHeight(44)
        self._execute_btn.setStyleSheet(DesignSystem.get_primary_button_style())
        self._execute_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        icon_manager.set_button_icon(
            self._execute_btn, "arrow-right",
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
        prog_layout.addWidget(
            self._progress_label, 0, Qt.AlignmentFlag.AlignCenter,
        )

        self._progress_status = QLabel("")
        self._progress_status.setStyleSheet(DesignSystem.get_strategy_info_text_style())
        prog_layout.addWidget(
            self._progress_status, 0, Qt.AlignmentFlag.AlignCenter,
        )

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setStyleSheet(DesignSystem.get_progressbar_style())
        self._progress_bar.setFixedWidth(400)
        prog_layout.addWidget(
            self._progress_bar, 0, Qt.AlignmentFlag.AlignCenter,
        )

        self._cancel_btn = QPushButton(tr("strategy.cancel"))
        self._cancel_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        self._cancel_btn.clicked.connect(self._on_cancel)
        prog_layout.addWidget(
            self._cancel_btn, 0, Qt.AlignmentFlag.AlignCenter,
        )

        self._progress_container.setVisible(False)
        lay.addWidget(self._progress_container)

        lay.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll)

    # ------------------------------------------------------------------
    # File table
    # ------------------------------------------------------------------

    def _rebuild_table(self) -> None:
        """Build the file table with original names and predicted output names."""
        while self._table_container.count():
            item = self._table_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._files:
            return

        # Header row
        header = QFrame()
        header.setStyleSheet(DesignSystem.get_file_table_header_style())
        hl = QHBoxLayout(header)
        hl.setContentsMargins(12, 6, 12, 6)
        hl.setSpacing(8)

        # Add number column header only for numbering tool
        if self._tool == ToolName.NUMBER:
            num_lbl = QLabel(tr("simple_tool.number_header"))
            num_lbl.setStyleSheet(DesignSystem.get_table_header_cell_style())
            num_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            num_lbl.setFixedWidth(60)
            hl.addWidget(num_lbl)

        # For merge tool, add order column
        if self._tool == ToolName.MERGE:
            order_lbl = QLabel("#")
            order_lbl.setStyleSheet(DesignSystem.get_table_header_cell_style())
            order_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            order_lbl.setFixedWidth(60)
            hl.addWidget(order_lbl)

        file_lbl = QLabel(tr("simple_tool.files_header"))
        file_lbl.setStyleSheet(DesignSystem.get_table_header_cell_style())
        hl.addWidget(file_lbl, 3)

        # All tools show output/status column
        if self._tool == ToolName.MERGE:
            # For merge, show a status column (drag handle)
            drag_lbl = QLabel("")
            drag_lbl.setStyleSheet(DesignSystem.get_table_header_cell_style())
            drag_lbl.setFixedWidth(30)
            hl.addWidget(drag_lbl)
        elif self._tool == ToolName.NUMBER:
            # For numbering, show output column
            out_lbl = QLabel(tr("simple_tool.output_header"))
            out_lbl.setStyleSheet(DesignSystem.get_table_header_cell_style())
            hl.addWidget(out_lbl, 3)
            # And drag handle column
            drag_lbl = QLabel("")
            drag_lbl.setStyleSheet(DesignSystem.get_table_header_cell_style())
            drag_lbl.setFixedWidth(30)
            hl.addWidget(drag_lbl)
        else:
            out_lbl = QLabel(tr("simple_tool.output_header"))
            out_lbl.setStyleSheet(DesignSystem.get_table_header_cell_style())
            hl.addWidget(out_lbl, 3)

        self._table_container.addWidget(header)

        # Data rows - for certain tools, show encrypted files at the end
        if self._tool in (ToolName.MERGE, ToolName.NUMBER, ToolName.STRIP_METADATA):
            # Separate files into processable and non-processable
            processable_indices = []
            non_processable_indices = []
            
            for i in range(len(self._files)):
                is_encrypted = self._file_encryption_status.get(i, False)
                if is_encrypted:
                    non_processable_indices.append(i)
                else:
                    processable_indices.append(i)
            
            # Show processable files first, then non-processable
            sorted_indices = processable_indices + non_processable_indices
            
            for i in sorted_indices:
                row = self._build_file_row(i, self._files[i])
                self._table_container.addWidget(row)
        else:
            # For other tools, show files in original order
            for i, path in enumerate(self._files):
                row = self._build_file_row(i, path)
                self._table_container.addWidget(row)

    def _build_file_row(self, idx: int, path: Path) -> QFrame:
        """Build a single row showing original name, output name, and actions."""
        # Check if file is encrypted
        is_encrypted = self._file_encryption_status.get(idx, False)
        
        # Use DraggableFileRow for merge and numbering tools to enable drag and drop reordering
        # But only if the file is not encrypted
        if self._tool in (ToolName.MERGE, ToolName.NUMBER):
            row = DraggableFileRow(idx, is_draggable=not is_encrypted)
            row.rowMoved.connect(self._on_row_moved)
        else:
            row = QFrame()
            
        row.setStyleSheet(DesignSystem.get_file_table_row_style(idx % 2 == 0))

        rl = QHBoxLayout(row)
        rl.setContentsMargins(12, 3, 12, 3)
        rl.setSpacing(8)

        # Check if file is encrypted
        is_encrypted = self._file_encryption_status.get(idx, False)

        # Add number column only for numbering tool
        if self._tool == ToolName.NUMBER:
            if is_encrypted:
                # Show empty space or dash for encrypted files
                num_lbl = QLabel("—")
                num_lbl.setStyleSheet(
                    f"font-size: {DesignSystem.FONT_SIZE_MD}px;"
                    f"color: {DesignSystem.COLOR_TEXT_SECONDARY};"
                )
            else:
                # Calculate the number for non-encrypted files only
                # Count how many non-encrypted files come before this one
                non_encrypted_before = sum(
                    1 for i in range(idx)
                    if not self._file_encryption_status.get(i, False)
                )
                number_to_assign = self._start_spin.value() + non_encrypted_before
                num_lbl = QLabel(str(number_to_assign))
                num_lbl.setStyleSheet(
                    f"font-size: {DesignSystem.FONT_SIZE_MD}px;"
                    f"font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
                    f"color: {DesignSystem.COLOR_PRIMARY};"
                )
            num_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            num_lbl.setFixedWidth(60)
            rl.addWidget(num_lbl)

        # For merge tool, show order index
        if self._tool == ToolName.MERGE:
            if is_encrypted:
                # Show empty space or dash for encrypted files
                idx_lbl = QLabel("—")
                idx_lbl.setStyleSheet(
                    f"font-size: {DesignSystem.FONT_SIZE_MD}px;"
                    f"color: {DesignSystem.COLOR_TEXT_SECONDARY};"
                )
            else:
                # Calculate the order for non-encrypted files only
                # Count how many non-encrypted files come before this one
                non_encrypted_before = sum(
                    1 for i in range(idx)
                    if not self._file_encryption_status.get(i, False)
                )
                order_number = non_encrypted_before + 1
                idx_lbl = QLabel(f"{order_number}.")
                idx_lbl.setStyleSheet(
                    f"font-size: {DesignSystem.FONT_SIZE_MD}px;"
                    f"font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
                    f"color: {DesignSystem.COLOR_PRIMARY};"
                )
            idx_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            idx_lbl.setFixedWidth(60)
            rl.addWidget(idx_lbl)

        # Original file with eye button and styled path
        name_container = QWidget()
        name_container.setStyleSheet("QWidget { border: none; background: transparent; }")
        name_layout = QHBoxLayout(name_container)
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(6)
        
        # Eye button to open PDF (left side)
        eye_btn = QToolButton()
        eye_btn.setToolTip(tr("simple_tool.open_file"))
        icon_manager.set_button_icon(
            eye_btn, "eye", color=DesignSystem.COLOR_PRIMARY, size=16,
        )
        eye_btn.setStyleSheet(DesignSystem.get_icon_button_style())
        eye_btn.setFixedSize(28, 28)
        eye_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        eye_btn.clicked.connect(
            lambda _=False, p=path: self._open_pdf(p),
        )
        name_layout.addWidget(eye_btn)
        
        # Path and filename with different styling
        path_parent = str(path.parent) if path.parent != Path('.') else ''
        path_name = path.name
        
        if path_parent:
            # Show path in gray and filename in bold (not blue)
            full_text = f'<span style="color: {DesignSystem.COLOR_TEXT_SECONDARY};">{path_parent}/</span><span style="color: {DesignSystem.COLOR_TEXT}; font-weight: {DesignSystem.FONT_WEIGHT_BOLD};">{path_name}</span>'
        else:
            # Only filename in bold (not blue)
            full_text = f'<span style="color: {DesignSystem.COLOR_TEXT}; font-weight: {DesignSystem.FONT_WEIGHT_BOLD};">{path_name}</span>'
        
        name_lbl = ElidedLabel()
        name_lbl.setText(full_text)
        name_lbl.setTextFormat(Qt.TextFormat.RichText)
        name_lbl.setStyleSheet(f"font-size: {DesignSystem.FONT_SIZE_SM}px;")
        name_lbl.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        name_lbl.customContextMenuRequested.connect(
            lambda pos, i=idx, w=name_lbl: self._show_source_context_menu(w, pos, i),
        )
        name_layout.addWidget(name_lbl, 1)
        
        rl.addWidget(name_container, 3)

        # For merge tool, check if file is encrypted and show message or drag handle
        if self._tool == ToolName.MERGE:
            is_encrypted = self._file_encryption_status.get(idx, False)
            if is_encrypted:
                # Show encrypted warning in a wider column
                encrypted_label = QLabel(tr("simple_tool.encrypted_not_processable"))
                encrypted_label.setStyleSheet(
                    f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
                    f"color: {DesignSystem.COLOR_WARNING};"
                    f"font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
                    f"font-style: italic;"
                    f"background: transparent;"
                    f"border: none;"
                )
                encrypted_label.setFixedWidth(30)
                rl.addWidget(encrypted_label)
            else:
                # Drag handle icon for non-encrypted files
                drag_handle = QLabel()
                icon_manager.set_label_icon(drag_handle, "grip-vertical", color=DesignSystem.COLOR_TEXT_SECONDARY, size=20)
                drag_handle.setToolTip(tr("merge_screen.drag_to_reorder") if tr("merge_screen.drag_to_reorder") != "merge_screen.drag_to_reorder" else "Drag to reorder")
                drag_handle.setFixedWidth(30)
                drag_handle.setAlignment(Qt.AlignmentFlag.AlignCenter)
                drag_handle.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
                rl.addWidget(drag_handle)
        elif self._tool == ToolName.NUMBER:
            # For numbering tool, show output name and drag handle
            is_encrypted = self._file_encryption_status.get(idx, False)
            if is_encrypted:
                # Show encrypted warning
                encrypted_label = QLabel(tr("simple_tool.encrypted_not_processable"))
                encrypted_label.setStyleSheet(
                    f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
                    f"color: {DesignSystem.COLOR_WARNING};"
                    f"font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
                    f"font-style: italic;"
                    f"background: transparent;"
                    f"border: none;"
                )
                rl.addWidget(encrypted_label, 3)
                # Empty space for drag handle
                spacer_drag = QWidget()
                spacer_drag.setFixedWidth(30)
                rl.addWidget(spacer_drag)
            else:
                # Show output name for non-encrypted files
                output_name = self._get_output_name(idx)
                out_edit = QLineEdit(output_name)
                out_edit.setStyleSheet(
                    DesignSystem.get_line_edit_style().replace(
                        DesignSystem.COLOR_TEXT, DesignSystem.COLOR_PRIMARY,
                    )
                )
                out_edit.textChanged.connect(
                    lambda text, i=idx: self._on_output_name_changed(i, text)
                )
                rl.addWidget(out_edit, 3)
                # Drag handle icon for non-encrypted files
                drag_handle = QLabel()
                icon_manager.set_label_icon(drag_handle, "grip-vertical", color=DesignSystem.COLOR_TEXT_SECONDARY, size=20)
                drag_handle.setToolTip(tr("merge_screen.drag_to_reorder") if tr("merge_screen.drag_to_reorder") != "merge_screen.drag_to_reorder" else "Drag to reorder")
                drag_handle.setFixedWidth(30)
                drag_handle.setAlignment(Qt.AlignmentFlag.AlignCenter)
                drag_handle.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
                rl.addWidget(drag_handle)
        else:
            # Check if file is encrypted — encrypted files are not processable
            is_encrypted = self._file_encryption_status.get(idx, False)

            if is_encrypted:
                encrypted_label = QLabel(tr("simple_tool.encrypted_not_processable"))
                encrypted_label.setStyleSheet(
                    f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
                    f"color: {DesignSystem.COLOR_WARNING};"
                    f"font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
                    f"font-style: italic;"
                    f"background: transparent;"
                    f"border: none;"
                )
                rl.addWidget(encrypted_label, 3)
            else:
                # Show output name for non-encrypted files
                output_name = self._get_output_name(idx)
                out_edit = QLineEdit(output_name)
                out_edit.setStyleSheet(
                    DesignSystem.get_line_edit_style().replace(
                        DesignSystem.COLOR_TEXT, DesignSystem.COLOR_PRIMARY,
                    )
                )
                out_edit.textChanged.connect(
                    lambda text, i=idx: self._on_output_name_changed(i, text)
                )
                rl.addWidget(out_edit, 3)

        return row

    def _get_output_name(self, idx: int) -> str:
        """Get the predicted (or custom) output file name for file at *idx*."""
        if idx in self._output_names:
            return self._output_names[idx]
        path = self._files[idx]
        predicted = output_path_for(path)
        return predicted.name

    def _on_output_name_changed(self, idx: int, text: str) -> None:
        """Handle when user edits the output name directly in the table."""
        text = text.strip()
        if text:
            self._output_names[idx] = text

    def _move_file(self, idx: int, delta: int) -> None:
        """Move file at idx by delta positions (for merge tool reordering)."""
        new_idx = idx + delta
        if 0 <= new_idx < len(self._files):
            self._files[idx], self._files[new_idx] = self._files[new_idx], self._files[idx]
            self._rebuild_table()
    
    def _on_row_moved(self, from_idx: int, to_idx: int) -> None:
        """Handle drag and drop reordering of files."""
        if from_idx == to_idx or from_idx < 0 or to_idx < 0:
            return
        if from_idx >= len(self._files) or to_idx >= len(self._files):
            return
            
        # Move the file from from_idx to to_idx
        file_to_move = self._files.pop(from_idx)
        self._files.insert(to_idx, file_to_move)
        
        # Also move custom output names if they exist
        if from_idx in self._output_names:
            name = self._output_names.pop(from_idx)
            # Adjust indices for other custom names
            new_names = {}
            for old_idx, custom_name in self._output_names.items():
                if old_idx < from_idx and old_idx < to_idx:
                    new_names[old_idx] = custom_name
                elif old_idx > from_idx and old_idx > to_idx:
                    new_names[old_idx] = custom_name
                elif old_idx < from_idx and old_idx >= to_idx:
                    new_names[old_idx + 1] = custom_name
                elif old_idx > from_idx and old_idx <= to_idx:
                    new_names[old_idx - 1] = custom_name
            new_names[to_idx] = name
            self._output_names = new_names
        else:
            # Adjust indices for all custom names
            new_names = {}
            for old_idx, custom_name in self._output_names.items():
                if old_idx < from_idx and old_idx < to_idx:
                    new_names[old_idx] = custom_name
                elif old_idx > from_idx and old_idx > to_idx:
                    new_names[old_idx] = custom_name
                elif old_idx < from_idx and old_idx >= to_idx:
                    new_names[old_idx + 1] = custom_name
                elif old_idx > from_idx and old_idx <= to_idx:
                    new_names[old_idx - 1] = custom_name
            self._output_names = new_names
        
        self._rebuild_table()

    def _on_filename_changed(self, text: str) -> None:
        """Update the output filename when the user types (for merge tool)."""
        self._output_filename = text.strip()

    # ------------------------------------------------------------------
    # Context menus
    # ------------------------------------------------------------------

    def _show_source_context_menu(
        self, widget: QWidget, pos, file_idx: int,
    ) -> None:
        """Context menu for source file column - only 'View details'."""
        menu = QMenu(self)
        menu.setStyleSheet(DesignSystem.get_context_menu_style())
        path = self._files[file_idx]

        view_action = menu.addAction(tr("simple_tool.view_details"))
        view_action.triggered.connect(
            lambda: self._show_details_for_file(path),
        )

        menu.exec(widget.mapToGlobal(pos))

    def _show_output_context_menu(
        self, widget: QWidget, pos, file_idx: int,
    ) -> None:
        """Context menu for output file column - only 'View details'."""
        menu = QMenu(self)
        menu.setStyleSheet(DesignSystem.get_context_menu_style())
        path = self._files[file_idx]

        view_action = menu.addAction(tr("simple_tool.view_details"))
        view_action.triggered.connect(
            lambda: self._show_details_for_file(path),
        )

        menu.exec(widget.mapToGlobal(pos))

    def _show_details_for_file(self, path: Path) -> None:
        """Open the details dialog for a specific file."""
        from safetool_pdf_core.analyzer import analyze
        from safetool_pdf_desktop.dialogs.details_dialog import DetailsDialog

        _logger.info(f"Showing details for file: {path}")
        try:
            _logger.debug("Analyzing PDF...")
            analysis = analyze(path)
            _logger.debug(f"Analysis completed: {analysis}")
        except Exception as exc:
            _logger.error(f"Failed to analyze PDF: {exc}", exc_info=True)
            return
        
        try:
            _logger.debug("Creating DetailsDialog...")
            dlg = DetailsDialog(analysis, parent=self)
            _logger.debug("Showing dialog...")
            dlg.exec()
            _logger.info("Dialog closed")
        except Exception as exc:
            _logger.error(f"Failed to show details dialog: {exc}", exc_info=True)

    def _open_pdf(self, path: Path) -> None:
        """Open a PDF file with the platform's default viewer."""
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_tool(self, tool: ToolName, files: list[Path]) -> None:
        """Configure this screen for *tool* and the given *files*."""
        self._tool = tool
        self._files = list(files)
        self._output_names = {}
        self._worker = None
        self._file_encryption_status = {}  # Track which files are encrypted

        meta = _TOOL_META.get(tool, {})

        # Title & icon
        self._title_label.setText(tr(meta.get("title_key", "")))
        self._subtitle_label.setText(tr(meta.get("subtitle_key", "")))
        icon_manager.set_label_icon(
            self._tool_icon, meta.get("icon", "file-pdf"),
            color=meta.get("color", DesignSystem.COLOR_PRIMARY), size=24,
        )

        # File info
        total_size = sum(f.stat().st_size for f in files if f.is_file())
        self._file_info_label.setText(
            tr("simple_tool.files_info",
               count=len(files), size=_format_size(total_size)),
        )

        # Show/hide config widgets
        self._number_row.setVisible(tool == ToolName.NUMBER)
        self._merge_row.setVisible(tool == ToolName.MERGE)
        self._config_container.setVisible(tool in (ToolName.NUMBER, ToolName.MERGE))

        # Reset state
        self._execute_btn.setVisible(True)
        self._progress_container.setVisible(False)
        self._start_spin.setValue(1)
        self._output_filename = "merged"
        self._output_filename_input.setText(self._output_filename)

        # Update button text for merge
        if tool == ToolName.MERGE:
            self._execute_btn.setText(f"  {tr('merge_screen.btn_merge')}")
            icon_manager.set_button_icon(
                self._execute_btn, "file-multiple",
                color=DesignSystem.COLOR_PRIMARY_TEXT, size=18,
            )
        else:
            self._execute_btn.setText(f"  {tr('simple_tool.btn_execute')}")
            icon_manager.set_button_icon(
                self._execute_btn, "arrow-right",
                color=DesignSystem.COLOR_PRIMARY_TEXT, size=18,
            )

        # Analyze files to detect encryption status for all tools
        self._analyze_encryption_status()

        self._rebuild_table()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_start_number_changed(self, value: int) -> None:
        """Rebuild table when start number changes to update the number column."""
        if self._tool == ToolName.NUMBER:
            self._rebuild_table()

    def _analyze_encryption_status(self) -> None:
        """Analyze each file to determine if it's encrypted."""
        from safetool_pdf_core.analyzer import analyze

        self._file_encryption_status.clear()
        for idx, path in enumerate(self._files):
            try:
                result = analyze(path)
                self._file_encryption_status[idx] = result.is_encrypted
            except Exception:
                # If analysis fails, assume it might be encrypted
                self._file_encryption_status[idx] = True

    def _on_back(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            self._worker.request_cancel()
            self._worker.wait(2000)
        self.go_back.emit()

    def _on_execute(self) -> None:
        if not self._files or self._tool is None:
            return

        kwargs: dict = {}
        files_to_process = self._files
        
        if self._tool == ToolName.MERGE:
            # Use merge worker
            from safetool_pdf_desktop.workers.merge_worker import MergeWorker
            
            # Filter out encrypted files
            files_to_process = [
                f for idx, f in enumerate(self._files)
                if not self._file_encryption_status.get(idx, False)
            ]
            
            # If no files to process, show message and return
            if not files_to_process:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.information(
                    self,
                    tr("merge_screen.title"),
                    tr("simple_tool.no_processable_files"),
                )
                return
            
            filename = self._output_filename.strip()
            if not filename:
                filename = "merged"
            
            self._execute_btn.setVisible(False)
            self._progress_container.setVisible(True)
            self._progress_bar.setValue(0)
            self._progress_status.setText("")
            
            self._worker = MergeWorker(
                files_to_process,
                output_filename=filename,
                parent=self,
            )
        else:
            # Use simple tool worker
            from safetool_pdf_desktop.workers.simple_tool_worker import SimpleToolWorker
            
            if self._tool == ToolName.NUMBER:
                kwargs["start_number"] = self._start_spin.value()
                # Filter out encrypted files
                files_to_process = [
                    f for idx, f in enumerate(self._files)
                    if not self._file_encryption_status.get(idx, False)
                ]
                
                # If no files to process, show message and return
                if not files_to_process:
                    from PySide6.QtWidgets import QMessageBox
                    QMessageBox.information(
                        self,
                        tr("simple_tool.numbering_title"),
                        tr("simple_tool.no_processable_files"),
                    )
                    return
            elif self._tool == ToolName.STRIP_METADATA:
                # Filter out encrypted files
                files_to_process = [
                    f for idx, f in enumerate(self._files)
                    if not self._file_encryption_status.get(idx, False)
                ]
                
                # If no files to process, show message and return
                if not files_to_process:
                    from PySide6.QtWidgets import QMessageBox
                    QMessageBox.information(
                        self,
                        tr("simple_tool.metadata_title"),
                        tr("simple_tool.no_processable_files"),
                    )
                    return
            self._execute_btn.setVisible(False)
            self._progress_container.setVisible(True)
            self._progress_bar.setValue(0)
            self._progress_status.setText("")

            self._worker = SimpleToolWorker(
                self._tool, files_to_process, parent=self, **kwargs,
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
        # Rename output files if user changed names
        self._apply_custom_renames(results)
        self.tool_complete.emit(self._tool, self._files, results)

    def _apply_custom_renames(self, results: list[ToolResult]) -> None:
        """Rename output files to match user-customised names (not for merge tool)."""
        if self._tool == ToolName.MERGE:
            return  # Merge tool handles its own output naming
        
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
                    _logger.warning(
                        "Failed to rename %s to %s", result.output_path, new_path,
                    )

    @Slot(str)
    def _on_error(self, msg: str) -> None:
        self._worker = None
        self._execute_btn.setVisible(True)
        self._progress_container.setVisible(False)
        self._progress_status.setText(msg)


