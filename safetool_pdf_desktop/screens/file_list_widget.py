# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Scrollable file list widget with per-file removal and context menu."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

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


class FileListRow(QFrame):
    """Single row in the file list: icon + name + size + remove button."""

    remove_clicked = Signal(Path)
    view_details_requested = Signal(Path)

    def __init__(self, path: Path, even: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._path = path
        self.setStyleSheet(DesignSystem.get_file_list_row_style(even))
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            DesignSystem.SPACE_12, DesignSystem.SPACE_6,
            DesignSystem.SPACE_12, DesignSystem.SPACE_6,
        )
        layout.setSpacing(DesignSystem.SPACE_8)

        # PDF icon
        icon_label = QLabel()
        icon_manager.set_label_icon(
            icon_label, 'file-pdf',
            color=DesignSystem.COLOR_PRIMARY, size=16,
        )
        layout.addWidget(icon_label)

        # Filename (elided)
        name_label = QLabel(self._path.name)
        name_label.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};"
            f"color: {DesignSystem.COLOR_TEXT};"
            f"background: transparent; border: none;"
        )
        layout.addWidget(name_label, 1)

        # File size
        try:
            size = self._path.stat().st_size
            size_text = _format_size(size)
        except OSError:
            size_text = "—"
        size_label = QLabel(size_text)
        size_label.setStyleSheet(
            f"font-family: {DesignSystem.FONT_FAMILY_MONO};"
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f"background: transparent; border: none;"
        )
        size_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        size_label.setMinimumWidth(70)
        layout.addWidget(size_label)

        # Remove button
        remove_btn = QToolButton()
        remove_btn.setAutoRaise(True)
        remove_btn.setToolTip(tr("file_list.remove_file"))
        icon_manager.set_button_icon(
            remove_btn, 'close-circle',
            color=DesignSystem.COLOR_TEXT_SECONDARY, size=16,
        )
        remove_btn.setStyleSheet(DesignSystem.get_file_list_remove_button_style())
        remove_btn.clicked.connect(lambda: self.remove_clicked.emit(self._path))
        layout.addWidget(remove_btn)

    @property
    def path(self) -> Path:
        return self._path

    def contextMenuEvent(self, event) -> None:  # noqa: N802
        menu = QMenu(self)
        menu.setStyleSheet(DesignSystem.get_context_menu_style())
        view_action = menu.addAction(tr("file_list.view_details"))
        view_action.triggered.connect(
            lambda: self.view_details_requested.emit(self._path)
        )
        menu.addSeparator()
        remove_action = menu.addAction(tr("file_list.remove"))
        remove_action.triggered.connect(
            lambda: self.remove_clicked.emit(self._path)
        )
        menu.exec(event.globalPos())


class FileListWidget(QWidget):
    """Scrollable list of selected PDF files with removal support."""

    files_changed = Signal(list)  # list[Path] — emitted when the list changes
    file_removed = Signal(Path)
    view_details_requested = Signal(Path)  # right-click → View Details

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._files: list[Path] = []
        self._build_ui()

    def _build_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet(DesignSystem.get_file_list_container_style())
        self._scroll.setMinimumHeight(80)
        self._scroll.setMaximumHeight(250)

        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)
        self._content_layout.addStretch()

        self._scroll.setWidget(self._content)
        outer_layout.addWidget(self._scroll)

        # Empty state label
        self._empty_label = QLabel(tr("file_list.no_files"))
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f"padding: {DesignSystem.SPACE_16}px;"
        )
        self._content_layout.insertWidget(0, self._empty_label)

    def set_files(self, files: list[Path]) -> None:
        """Replace the file list entirely."""
        resolved = []
        seen: set[str] = set()
        for f in files:
            key = str(f.resolve())
            if key not in seen:
                seen.add(key)
                resolved.append(f)
        self._files = resolved
        self._rebuild()
        self.files_changed.emit(list(self._files))

    def add_files(self, files: list[Path]) -> None:
        """Add files to the list (deduplicating by absolute path)."""
        seen = {str(f.resolve()) for f in self._files}
        for f in files:
            key = str(f.resolve())
            if key not in seen:
                seen.add(key)
                self._files.append(f)
        self._rebuild()
        self.files_changed.emit(list(self._files))

    def remove_file(self, path: Path) -> None:
        """Remove a single file from the list."""
        key = str(path.resolve())
        self._files = [f for f in self._files if str(f.resolve()) != key]
        self._rebuild()
        self.file_removed.emit(path)
        self.files_changed.emit(list(self._files))

    def get_files(self) -> list[Path]:
        """Return the current list of files."""
        return list(self._files)

    def _rebuild(self) -> None:
        """Rebuild all rows from current file list."""
        # Remove old rows
        while self._content_layout.count() > 0:
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._files:
            self._empty_label = QLabel(tr("file_list.no_files"))
            self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._empty_label.setStyleSheet(
                f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
                f"color: {DesignSystem.COLOR_TEXT_SECONDARY};"
                f"padding: {DesignSystem.SPACE_16}px;"
            )
            self._content_layout.addWidget(self._empty_label)
        else:
            for i, f in enumerate(self._files):
                row = FileListRow(f, even=(i % 2 == 0))
                row.remove_clicked.connect(self.remove_file)
                row.view_details_requested.connect(self.view_details_requested)
                self._content_layout.addWidget(row)

        self._content_layout.addStretch()
