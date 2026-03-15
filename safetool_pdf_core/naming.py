# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Output file naming — suffix ``_safetoolhub`` with collision handling."""

from __future__ import annotations

from pathlib import Path

from safetool_pdf_core.constants import OUTPUT_SUFFIX

def output_path_for(
    input_path: Path,
    output_dir: Path | None = None,
    suffix: str = OUTPUT_SUFFIX,
) -> Path:
    """Compute the output path for a given input PDF.

    Pattern: ``<stem>_safetoolhub.pdf``
    Collisions: ``<stem>_safetoolhub (1).pdf``, ``(2)``, etc.

    Parameters
    ----------
    input_path:
        The original PDF file path.
    output_dir:
        Optional output directory.  Defaults to the same directory as *input_path*.
    suffix:
        Suffix to append before the extension.

    Returns
    -------
    Path
        A non-existing output path.
    """
    stem = input_path.stem
    ext = input_path.suffix or ".pdf"
    directory = output_dir if output_dir is not None else input_path.parent

    candidate = directory / f"{stem}{suffix}{ext}"
    if not candidate.exists():
        return candidate

    counter = 1
    while True:
        candidate = directory / f"{stem}{suffix} ({counter}){ext}"
        if not candidate.exists():
            return candidate
        counter += 1
        if counter > 9999:
            raise RuntimeError("Too many output file collisions.")
