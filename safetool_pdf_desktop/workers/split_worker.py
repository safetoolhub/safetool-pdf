# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Worker for the split tool."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal

from safetool_pdf_core.models import ProgressInfo, SplitMode, ToolResult
from safetool_pdf_desktop.workers.base_worker import BaseWorker


class SplitWorker(BaseWorker):
    """Run PDF split in a background thread.

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
        mode: SplitMode,
        options: dict,
        suffix: str = "parte",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._files = files
        self._mode = mode
        self._options = options
        self._suffix = suffix

    def run(self) -> None:  # noqa: D401
        try:
            from safetool_pdf_core.tools.split import split_batch

            results = split_batch(
                self._files,
                mode=self._mode,
                options=self._options,
                suffix=self._suffix,
                progress_cb=self._on_progress,
                cancel=self._cancel,
            )
            self.finished.emit(results)
        except Exception as exc:
            self.error.emit(str(exc))

    def _on_progress(self, info: ProgressInfo) -> None:
        self.progress.emit(info)
