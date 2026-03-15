# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Screen 1: File selection — drop zone + file dialog."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from safetool_pdf_desktop.styles.design_system import DesignSystem
from safetool_pdf_desktop.styles.icons import icon_manager

class DropZoneWidget(QFrame):
    """Drag-and-drop area for PDF files."""

    files_dropped = Signal(list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumSize(400, 250)
        self.setStyleSheet(DesignSystem.get_dropzone_style(dragging=False))
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(DesignSystem.SPACE_16)

        # Icon
        icon_label = QLabel()
        icon_manager.set_label_icon(
            icon_label, 'file-pdf',
            color=DesignSystem.COLOR_PRIMARY, size=64,
        )
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        # Main text
        main_text = QLabel("Drop PDF files here")
        main_text.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_LG}px;"
            f"font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};"
            f"color: {DesignSystem.COLOR_TEXT};"
            f"background: transparent;"
            f"border: none;"
        )
        main_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(main_text)

        # Hint text
        hint_text = QLabel("or click the button below to browse")
        hint_text.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f"background: transparent;"
            f"border: none;"
        )
        hint_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint_text)

    # --- Drag & Drop ---

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith('.pdf'):
                    event.acceptProposedAction()
                    self.setStyleSheet(DesignSystem.get_dropzone_style(dragging=True))
                    return
        event.ignore()

    def dragLeaveEvent(self, event) -> None:  # noqa: N802
        self.setStyleSheet(DesignSystem.get_dropzone_style(dragging=False))

    def dropEvent(self, event) -> None:  # noqa: N802
        self.setStyleSheet(DesignSystem.get_dropzone_style(dragging=False))
        paths: list[Path] = []
        for url in event.mimeData().urls():
            local = url.toLocalFile()
            if local.lower().endswith('.pdf'):
                paths.append(Path(local))
        if paths:
            self.files_dropped.emit(paths)

class FileSelectionScreen(QWidget):
    """Screen 1 — File selection via drop zone or file dialog."""

    files_selected = Signal(list)  # list[Path]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(DesignSystem.SPACE_24)

        # Spacer top
        layout.addStretch(1)

        # Drop zone
        self._drop_zone = DropZoneWidget()
        self._drop_zone.files_dropped.connect(self.files_selected.emit)
        layout.addWidget(self._drop_zone, 0, Qt.AlignmentFlag.AlignCenter)

        # Browse button
        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        browse_btn = QPushButton("  Browse Files…")
        icon_manager.set_button_icon(
            browse_btn, 'folder-open',
            color=DesignSystem.COLOR_PRIMARY_TEXT, size=18,
        )
        browse_btn.setStyleSheet(DesignSystem.get_primary_button_style())
        browse_btn.setMinimumWidth(200)
        browse_btn.clicked.connect(self._browse_files)
        btn_row.addWidget(browse_btn)

        layout.addLayout(btn_row)

        # Supported formats hint
        formats_label = QLabel("Supports PDF files — single or multiple selection")
        formats_label.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"color: {DesignSystem.COLOR_TEXT_SECONDARY};"
        )
        formats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(formats_label)

        # Spacer bottom
        layout.addStretch(1)

    def _browse_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select PDF Files", "", "PDF Files (*.pdf)"
        )
        if paths:
            self.files_selected.emit([Path(p) for p in paths])
