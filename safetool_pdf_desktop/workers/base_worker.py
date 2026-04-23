# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Base worker thread with cancellation and common signals."""

from __future__ import annotations

import threading

from PySide6.QtCore import QThread, Signal


class BaseWorker(QThread):
    """Base class for background workers.

    Provides:
    - ``_cancel`` threading Event for cooperative cancellation.
    - ``request_cancel()`` method callable from any thread.
    - ``error`` signal for reporting exceptions.
    - ``progress_text`` signal for status messages.
    """

    error = Signal(str)
    progress_text = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._cancel = threading.Event()

    def request_cancel(self) -> None:
        """Request cooperative cancellation."""
        self._cancel.set()
