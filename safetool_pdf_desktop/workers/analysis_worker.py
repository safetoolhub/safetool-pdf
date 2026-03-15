# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Worker thread for PDF analysis."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from safetool_pdf_core.analyzer import analyze
from safetool_pdf_core.models import AnalysisResult

class AnalysisWorker(QThread):
    """Run analysis in a background thread.

    Signals
    -------
    finished : AnalysisResult
    error : str
    """

    finished = Signal(AnalysisResult)
    error = Signal(str)

    def __init__(self, path: Path, password: str | None = None, parent=None) -> None:
        super().__init__(parent)
        self._path = path
        self._password = password

    def run(self) -> None:
        try:
            result = analyze(self._path, password=self._password)
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))
