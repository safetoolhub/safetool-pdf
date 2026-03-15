# SafeTool PDF Desktop — PySide6 UI
# Copyright (C) 2026 safetoolhub.org
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Panel showing optimization results and size reduction."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from safetool_pdf_core.models import OptimizeResult


def _human_size(size_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(size_bytes) < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024  # type: ignore[assignment]
    return f"{size_bytes:.1f} TB"


class ResultsPanel(QWidget):
    """Displays optimization results with size comparison and action buttons."""

    open_file_requested = Signal(Path)
    open_folder_requested = Signal(Path)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)

        # Size comparison row
        sizes_row = QHBoxLayout()
        self._original_label = QLabel("Original: —")
        self._optimized_label = QLabel("Optimized: —")
        self._reduction_label = QLabel("Reduction: —")
        self._reduction_label.setStyleSheet("font-weight: bold;")
        sizes_row.addWidget(self._original_label)
        sizes_row.addWidget(self._optimized_label)
        sizes_row.addWidget(self._reduction_label)
        layout.addLayout(sizes_row)

        # Bar visualization
        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setFormat("%v % reduction")
        self._bar.setTextVisible(True)
        layout.addWidget(self._bar)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._open_file_btn = QPushButton("Open File")
        self._open_file_btn.setEnabled(False)
        self._open_file_btn.clicked.connect(self._emit_open_file)
        btn_row.addWidget(self._open_file_btn)

        self._open_folder_btn = QPushButton("Open Folder")
        self._open_folder_btn.setEnabled(False)
        self._open_folder_btn.clicked.connect(self._emit_open_folder)
        btn_row.addWidget(self._open_folder_btn)

        layout.addLayout(btn_row)

        self._result: OptimizeResult | None = None

    # -- public API -----------------------------------------------------------

    def set_result(self, result: OptimizeResult) -> None:
        """Populate the panel from an *OptimizeResult*."""
        self._result = result
        self._original_label.setText(f"Original: {_human_size(result.original_size)}")
        self._optimized_label.setText(
            f"Optimized: {_human_size(result.optimized_size)}"
        )
        pct = result.reduction_pct
        self._reduction_label.setText(f"Reduction: {pct:.1f} %")
        self._bar.setValue(int(pct))

        self._open_file_btn.setEnabled(True)
        self._open_folder_btn.setEnabled(True)

    # -- private slots --------------------------------------------------------

    def _emit_open_file(self) -> None:
        if self._result is not None:
            self.open_file_requested.emit(self._result.output_path)

    def _emit_open_folder(self) -> None:
        if self._result is not None:
            self.open_folder_requested.emit(self._result.output_path)
