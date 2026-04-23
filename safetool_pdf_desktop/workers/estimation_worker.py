# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Worker thread for estimating savings per file × per preset."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from PySide6.QtCore import Signal

from safetool_pdf_core.models import OptimizeOptions, OptimizeResult, PresetName
from safetool_pdf_core.tools.optimize import optimize
from safetool_pdf_core.tools.optimize import preset_by_name
from safetool_pdf_desktop.workers.base_worker import BaseWorker
from i18n import tr

# Preset display metadata (i18n label keys)
_PRESET_LABEL_KEYS: dict[PresetName, str] = {
    PresetName.LOSSLESS: "presets.lossless.label",
    PresetName.MODERATE: "presets.moderate.label",
    PresetName.AGGRESSIVE: "presets.aggressive.label",
}


class EstimationBatchWorker(BaseWorker):
    """Estimate savings for every file × every preset.

    Emits progress and a final dict keyed ``[file_index][PresetName]``.
    """

    file_preset_done = Signal(int, object, object)  # (index, PresetName, OptimizeResult|None)
    all_done = Signal(object)  # dict[int, dict[PresetName, OptimizeResult|None]]

    PRESETS = [PresetName.LOSSLESS, PresetName.MODERATE, PresetName.AGGRESSIVE]

    def __init__(self, files: list[Path], parent=None) -> None:
        super().__init__(parent)
        self._files = files

    def run(self) -> None:
        all_results: dict[int, dict[PresetName, OptimizeResult | None]] = {}
        total = len(self._files)
        tmp_dir = Path(tempfile.mkdtemp(prefix="safetool_pdf_est_"))

        try:
            for fi, path in enumerate(self._files):
                file_results: dict[PresetName, OptimizeResult | None] = {}
                for preset in self.PRESETS:
                    if self._cancel.is_set():
                        return
                    key = _PRESET_LABEL_KEYS.get(preset)
                    label = tr(key) if key else preset.value
                    self.progress_text.emit(
                        tr("strategy.estimating_pages",
                           preset=label, file=path.name,
                           current=fi + 1, total=total)
                    )
                    try:
                        options = preset_by_name(preset)
                        result = optimize(path, options, output_dir=tmp_dir)
                        file_results[preset] = result
                        self.file_preset_done.emit(fi, preset, result)
                    except Exception:
                        file_results[preset] = None
                        self.file_preset_done.emit(fi, preset, None)
                all_results[fi] = file_results

            if not self._cancel.is_set():
                self.all_done.emit(all_results)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


class CustomEstimationWorker(BaseWorker):
    """Estimate savings for every file with custom options."""

    file_done = Signal(int, object)  # (index, OptimizeResult|None)
    all_done = Signal(object)  # dict[int, OptimizeResult|None]

    def __init__(self, files: list[Path], options: OptimizeOptions, parent=None) -> None:
        super().__init__(parent)
        self._files = files
        self._options = options

    def run(self) -> None:
        results: dict[int, OptimizeResult | None] = {}
        total = len(self._files)
        tmp_dir = Path(tempfile.mkdtemp(prefix="safetool_pdf_cest_"))

        try:
            for fi, path in enumerate(self._files):
                if self._cancel.is_set():
                    return
                self.progress_text.emit(
                    f"Estimating Custom on {path.name} ({fi + 1}/{total})"
                )
                try:
                    result = optimize(path, self._options, output_dir=tmp_dir)
                    results[fi] = result
                    self.file_done.emit(fi, result)
                except Exception:
                    results[fi] = None
                    self.file_done.emit(fi, None)

            if not self._cancel.is_set():
                self.all_done.emit(results)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
