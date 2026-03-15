# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Optimizer tool package — PDF optimization with multiple strategies."""

from __future__ import annotations

from safetool_pdf_core.tools.optimize.optimize import optimize, optimize_batch
from safetool_pdf_core.tools.optimize.presets import (
    aggressive,
    cleanup_for,
    custom,
    lossless,
    moderate,
    preset_by_name,
    preset_requires_gs,
)

__all__ = [
    "optimize",
    "optimize_batch",
    "preset_by_name",
    "lossless",
    "moderate",
    "aggressive",
    "custom",
    "preset_requires_gs",
    "cleanup_for",
]
