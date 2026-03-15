# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Worker thread for rendering PDF page previews."""

from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage, QPixmap

class PreviewWorker(QThread):
    """Render page 1 of a PDF to QPixmap in a background thread.

    Signals
    -------
    finished : QPixmap, QPixmap  — (original, optimized)
    error : str
    """

    finished = Signal(QPixmap, QPixmap)
    error = Signal(str)

    def __init__(
        self,
        original_path: Path,
        optimized_path: Path,
        dpi: int = 150,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._original = original_path
        self._optimized = optimized_path
        self._dpi = dpi

    def run(self) -> None:
        try:
            orig_pix = self._render(self._original)
            opt_pix = self._render(self._optimized)
            self.finished.emit(orig_pix, opt_pix)
        except Exception as exc:
            self.error.emit(str(exc))

    def _render(self, path: Path) -> QPixmap:
        """Render page 0 of *path* to a QPixmap."""
        doc = fitz.open(str(path))
        try:
            page = doc.load_page(0)
            mat = fitz.Matrix(self._dpi / 72, self._dpi / 72)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            fmt = QImage.Format.Format_RGB888
            qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, fmt)
            return QPixmap.fromImage(qimg)
        finally:
            doc.close()
