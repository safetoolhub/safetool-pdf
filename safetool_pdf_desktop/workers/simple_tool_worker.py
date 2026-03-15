# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Worker for simple tools — numbering, metadata removal."""

from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import Signal

from safetool_pdf_core.models import ProgressInfo, ToolName, ToolResult
from safetool_pdf_desktop.workers.base_worker import BaseWorker


class SimpleToolWorker(BaseWorker):
    """Run a simple PDF tool in a background thread.

    Signals
    -------
    progress : ProgressInfo
    finished : list[ToolResult]
    """

    progress = Signal(ProgressInfo)
    finished = Signal(list)  # list[ToolResult]

    def __init__(
        self,
        tool: ToolName,
        files: list[Path],
        output_dir: Path | None = None,
        output_suffix: str = "",
        *,
        start_number: int = 1,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._tool = tool
        self._files = files
        self._output_dir = output_dir
        self._output_suffix = output_suffix
        self._start_number = start_number

    def run(self) -> None:  # noqa: D401
        try:
            from safetool_pdf_core.tools import numbering, strip_metadata

            dispatch = {
                ToolName.NUMBER: self._run_numbering,
                ToolName.STRIP_METADATA: self._run_metadata,
            }
            handler = dispatch.get(self._tool)
            if handler is None:
                self.error.emit(f"Unsupported tool: {self._tool}")
                return
            results = handler()
            self.finished.emit(results)
        except Exception as exc:
            self.error.emit(str(exc))

    def _on_progress(self, info: ProgressInfo) -> None:
        self.progress.emit(info)

    def _run_numbering(self) -> list[ToolResult]:
        from safetool_pdf_core.tools.numbering import execute
        return execute(
            self._files,
            output_dir=self._output_dir,
            output_suffix=self._output_suffix,
            start_number=self._start_number,
            progress_cb=self._on_progress,
            cancel=self._cancel,
        )

    def _run_metadata(self) -> list[ToolResult]:
        from safetool_pdf_core.tools.metadata import execute
        return execute(
            self._files,
            output_dir=self._output_dir,
            output_suffix=self._output_suffix,
            progress_cb=self._on_progress,
            cancel=self._cancel,
        )
