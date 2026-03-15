# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Progress callback protocol."""

from __future__ import annotations

from typing import Protocol

from safetool_pdf_core.models import ProgressInfo

class ProgressCallback(Protocol):
    """Callable that receives progress updates."""

    def __call__(self, info: ProgressInfo) -> None: ...

class CancellationToken(Protocol):
    """Object whose ``is_set()`` method returns True when cancellation is requested."""

    def is_set(self) -> bool: ...
