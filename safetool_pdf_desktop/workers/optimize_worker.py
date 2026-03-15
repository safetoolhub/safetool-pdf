# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Worker thread for PDF optimization (single and batch)."""

from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from safetool_pdf_core.models import OptimizeOptions, OptimizeResult, ProgressInfo
from safetool_pdf_core.tools.optimize import optimize, optimize_batch

class OptimizeWorker(QThread):
    """Run optimization in a background thread.

    Signals
    -------
    progress : ProgressInfo
    finished_one : OptimizeResult
    finished_all : list[OptimizeResult]
    error : str
    warning : str
    """

    progress = Signal(ProgressInfo)
    finished_one = Signal(OptimizeResult)
    finished_all = Signal(list)
    error = Signal(str)
    warning = Signal(str)

    def __init__(
        self,
        files: list[Path],
        options: OptimizeOptions,
        output_dir: Path | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._files = files
        self._options = options
        self._output_dir = output_dir
        self._cancel = threading.Event()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def request_cancel(self) -> None:
        """Request cancellation from any thread."""
        self._cancel.set()

    # ------------------------------------------------------------------
    # QThread override
    # ------------------------------------------------------------------

    def run(self) -> None:  # noqa: D401
        """Execute the optimization pipeline (runs in worker thread)."""
        try:
            if len(self._files) == 1:
                result = optimize(
                    self._files[0],
                    options=self._options,
                    output_dir=self._output_dir,
                    progress_cb=self._on_progress,
                    cancel=self._cancel,
                )
                self.finished_one.emit(result)
                self.finished_all.emit([result])
            else:
                results = optimize_batch(
                    self._files,
                    options=self._options,
                    output_dir=self._output_dir,
                    progress_cb=self._on_progress,
                    cancel=self._cancel,
                )
                self.finished_all.emit(results)
        except Exception as exc:
            self.error.emit(str(exc))

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_progress(self, info: ProgressInfo) -> None:
        self.progress.emit(info)
        for w in []:  # placeholder — warnings come via result
            self.warning.emit(w)
