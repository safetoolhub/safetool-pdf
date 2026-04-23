# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Worker for the merge tool."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal

from safetool_pdf_core.models import ProgressInfo, ToolResult
from safetool_pdf_desktop.workers.base_worker import BaseWorker


class MergeWorker(BaseWorker):
    """Run PDF merge in a background thread.

    Signals
    -------
    progress : ProgressInfo
    finished : list[ToolResult]
    """

    progress = Signal(ProgressInfo)
    finished = Signal(list)  # list[ToolResult]

    def __init__(
        self,
        files: list[Path],
        output_dir: Path | None = None,
        output_suffix: str = "",
        output_filename: str = "merged",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._files = files
        self._output_dir = output_dir
        self._output_suffix = output_suffix
        self._output_filename = output_filename

    def run(self) -> None:  # noqa: D401
        try:
            from safetool_pdf_core.tools.merge import execute

            results = execute(
                self._files,
                output_dir=self._output_dir,
                output_suffix=self._output_suffix,
                output_filename=self._output_filename,
                progress_cb=self._on_progress,
                cancel=self._cancel,
            )
            self.finished.emit(results)
        except Exception as exc:
            self.error.emit(str(exc))

    def _on_progress(self, info: ProgressInfo) -> None:
        self.progress.emit(info)
