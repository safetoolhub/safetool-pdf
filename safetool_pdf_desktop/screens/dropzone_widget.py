# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Drop zone widget for PDF file selection — innerpix-lab style."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from safetool_pdf_desktop.styles.design_system import DesignSystem
from safetool_pdf_desktop.styles.icons import icon_manager
from i18n import tr


class DropZoneWidget(QFrame):
    """Drag-and-drop area for PDF files — centred icon, text, and hint.

    The Browse button is NOT part of this widget; the parent screen
    places it below the drop zone.
    """

    files_dropped = Signal(list)  # list[Path]
    browse_requested = Signal()   # emitted on Ctrl+click or accessibility

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._is_dragging = False
        self._build_ui()
        self._apply_styles()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            DesignSystem.SPACE_24, DesignSystem.SPACE_20,
            DesignSystem.SPACE_24, DesignSystem.SPACE_20,
        )
        layout.setSpacing(DesignSystem.SPACE_12)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Make the entire area indicate it's clickable
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Icon
        self._icon_label = QLabel()
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setMinimumSize(64, 64)
        self._icon_label.setContentsMargins(0, 0, 0, 0)
        self._icon_label.setStyleSheet("padding: 0; margin: 0; border: none; background: transparent;")
        icon_manager.set_label_icon(
            self._icon_label, 'file-pdf',
            color=DesignSystem.COLOR_PRIMARY, size=64,
        )
        layout.addWidget(self._icon_label)

        # Main text
        self._main_text = QLabel(tr("dropzone.drop_here"))
        self._main_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._main_text.setFixedWidth(280)
        self._main_text.setStyleSheet(DesignSystem.get_dropzone_text_style())
        layout.addWidget(self._main_text)

        # Hint text
        self._hint_text = QLabel(tr("dropzone.browse_hint"))
        self._hint_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint_text.setStyleSheet(DesignSystem.get_dropzone_hint_style())
        
        self._hint_opacity = QGraphicsOpacityEffect(self._hint_text)
        self._hint_opacity.setOpacity(1.0)
        self._hint_text.setGraphicsEffect(self._hint_opacity)
        layout.addWidget(self._hint_text)

        # Minimum size for a comfortable drop target
        self.setMinimumSize(400, 180)

    def _apply_styles(self) -> None:
        self._update_appearance(dragging=False)

    def _update_appearance(self, dragging: bool = False) -> None:
        if dragging:
            self.setStyleSheet(DesignSystem.get_dropzone_style(dragging=True))
            self._main_text.setText(tr("dropzone.dragging"))
            self._hint_opacity.setOpacity(0.0)
        else:
            self.setStyleSheet(DesignSystem.get_dropzone_style(dragging=False))
            self._main_text.setText(tr("dropzone.drop_here"))
            self._hint_opacity.setOpacity(1.0)

    # --- Interaction ---
    
    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.browse_requested.emit()
            event.accept()
        else:
            super().mousePressEvent(event)

    # --- Drag & Drop ---

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith('.pdf'):
                    event.acceptProposedAction()
                    self._is_dragging = True
                    self._update_appearance(dragging=True)
                    return
        event.ignore()

    def dragLeaveEvent(self, event) -> None:  # noqa: N802
        self._is_dragging = False
        self._update_appearance(dragging=False)

    def dropEvent(self, event) -> None:  # noqa: N802
        self._is_dragging = False
        self._update_appearance(dragging=False)
        paths: list[Path] = []
        for url in event.mimeData().urls():
            local = url.toLocalFile()
            if local.lower().endswith('.pdf'):
                paths.append(Path(local))
        if paths:
            self.files_dropped.emit(paths)
