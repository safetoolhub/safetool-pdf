# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Worker for the unlock / permissions tool."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal

from safetool_pdf_core.models import PdfPermissions, ProgressInfo, ToolResult
from safetool_pdf_desktop.workers.base_worker import BaseWorker


class UnlockWorker(BaseWorker):
    """Run PDF unlock / permission modification in a background thread.

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
        password: str = "",
        output_dir: Path | None = None,
        output_suffix: str = "",
        *,
        new_permissions: PdfPermissions | None = None,
        new_user_password: str = "",
        new_owner_password: str = "",
        remove_encryption: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._files = files
        self._password = password
        self._output_dir = output_dir
        self._output_suffix = output_suffix
        self._new_permissions = new_permissions
        self._new_user_password = new_user_password
        self._new_owner_password = new_owner_password
        self._remove_encryption = remove_encryption

    def run(self) -> None:  # noqa: D401
        try:
            from safetool_pdf_core.tools.unlock import execute

            results = execute(
                self._files,
                password=self._password,
                output_dir=self._output_dir,
                output_suffix=self._output_suffix,
                new_permissions=self._new_permissions,
                new_user_password=self._new_user_password,
                new_owner_password=self._new_owner_password,
                remove_encryption=self._remove_encryption,
                progress_cb=self._on_progress,
                cancel=self._cancel,
            )
            self.finished.emit(results)
        except Exception as exc:
            self.error.emit(str(exc))

    def _on_progress(self, info: ProgressInfo) -> None:
        self.progress.emit(info)
