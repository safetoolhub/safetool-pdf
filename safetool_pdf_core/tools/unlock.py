# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Unlock tool — modify PDF permissions, passwords, and restrictions."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import pikepdf

from safetool_pdf_core.exceptions import CancellationError
from safetool_pdf_core.models import PdfPermissions, ProgressInfo, ToolName, ToolResult
from safetool_pdf_core.naming import output_path_for

if TYPE_CHECKING:
    from safetool_pdf_core.progress import CancellationToken, ProgressCallback

logger = logging.getLogger(__name__)

_STAGE = "unlock"


# ---------------------------------------------------------------------------
# Permission helpers
# ---------------------------------------------------------------------------

def read_permissions(path: Path, password: str = "") -> PdfPermissions:
    """Read the current permissions from a PDF.

    Returns a ``PdfPermissions`` with all flags set to ``True`` when the
    document has no encryption or no permission restrictions.

    Returns **effective** permissions: if the file is opened with owner
    privileges (owner password or no owner password set), returns all
    permissions as True regardless of stored /P value, since owner access
    grants full permissions.
    """
    try:
        open_kwargs: dict = {}
        if password:
            open_kwargs["password"] = password
        pdf = pikepdf.open(str(path), **open_kwargs)
    except pikepdf.PasswordError:
        # Cannot read — return all-True as default
        return PdfPermissions()

    try:
        if not pdf.encryption:
            return PdfPermissions()
        
        # Check if we have owner access
        # pdf.owner_password_matched is True when:
        # - Opened with owner password, or
        # - No owner password is set (empty owner password)
        # In both cases, we have full access regardless of /P value
        if pdf.owner_password_matched:
            return PdfPermissions()
        
        # Otherwise return the stored permissions (user access)
        a = pdf.allow
        return PdfPermissions(
            print_lowres=a.print_lowres,
            print_highres=a.print_highres,
            modify_other=a.modify_other,
            extract=a.extract,
            modify_annotation=a.modify_annotation,
            fill_forms=a.modify_form,
            accessibility=a.accessibility,
            modify_assembly=a.modify_assembly,
        )
    finally:
        pdf.close()


def read_stored_permissions(path: Path, password: str = "") -> PdfPermissions:
    """Read the stored permissions from a PDF (from /P value).

    Returns the permissions as stored in the PDF's encryption dictionary,
    regardless of whether the file was opened with owner or user access.
    This is useful for UI where you want to show/edit the actual stored
    permissions.

    Returns a ``PdfPermissions`` with all flags set to ``True`` when the
    document has no encryption.
    """
    try:
        open_kwargs: dict = {}
        if password:
            open_kwargs["password"] = password
        pdf = pikepdf.open(str(path), **open_kwargs)
    except pikepdf.PasswordError:
        # Cannot read — return all-True as default
        return PdfPermissions()

    try:
        if not pdf.encryption:
            return PdfPermissions()
        
        # Always return stored permissions from pdf.allow
        # regardless of owner_password_matched
        a = pdf.allow
        return PdfPermissions(
            print_lowres=a.print_lowres,
            print_highres=a.print_highres,
            modify_other=a.modify_other,
            extract=a.extract,
            modify_annotation=a.modify_annotation,
            fill_forms=a.modify_form,
            accessibility=a.accessibility,
            modify_assembly=a.modify_assembly,
        )
    finally:
        pdf.close()


def _decode_permissions(p_value: int) -> PdfPermissions:
    """Decode the /P integer into ``PdfPermissions``."""
    return PdfPermissions(
        print_lowres=bool(p_value & (1 << 2)),
        modify_other=bool(p_value & (1 << 3)),
        extract=bool(p_value & (1 << 4)),
        modify_annotation=bool(p_value & (1 << 5)),
        fill_forms=bool(p_value & (1 << 8)),
        accessibility=bool(p_value & (1 << 9)),
        modify_assembly=bool(p_value & (1 << 10)),
        print_highres=bool(p_value & (1 << 11)),
    )


def _to_pikepdf_permissions(perms: PdfPermissions) -> pikepdf.Permissions:
    """Convert ``PdfPermissions`` to ``pikepdf.Permissions``.

    Note: pikepdf automatically sets ``print_lowres=True`` when
    ``print_highres=True``, following PDF spec logic that high-quality
    printing implies low-quality printing is also allowed.
    """
    return pikepdf.Permissions(
        accessibility=perms.accessibility,
        extract=perms.extract,
        modify_annotation=perms.modify_annotation,
        modify_assembly=perms.modify_assembly,
        modify_form=perms.fill_forms,
        modify_other=perms.modify_other,
        print_lowres=perms.print_lowres,
        print_highres=perms.print_highres,
    )


# ---------------------------------------------------------------------------
# Main execute
# ---------------------------------------------------------------------------

def execute(
    input_paths: list[Path],
    password: str = "",
    output_dir: Path | None = None,
    output_suffix: str = "",
    *,
    new_permissions: PdfPermissions | None = None,
    new_user_password: str = "",
    new_owner_password: str = "",
    remove_encryption: bool = False,
    progress_cb: ProgressCallback | None = None,
    cancel: CancellationToken | None = None,
) -> list[ToolResult]:
    """Modify permissions / passwords on each input PDF.

    Modes of operation:
    * ``remove_encryption=True``: Saves without any encryption (removes all
      restrictions and passwords).
    * ``new_permissions`` provided: Sets the given permission flags. If
      ``new_user_password`` or ``new_owner_password`` are given they are also
      applied; otherwise the document is saved with an empty owner password
      and no user password.
    * Neither: legacy "unlock-only" behaviour — removes encryption entirely.

    Returns one ``ToolResult`` per input file.
    """
    results: list[ToolResult] = []
    total = len(input_paths)

    def _progress(msg: str, pct: float, fi: int = 0) -> None:
        if progress_cb is not None:
            progress_cb(ProgressInfo(
                stage=_STAGE, message=msg, percent=pct,
                file_index=fi, file_total=total,
            ))

    for idx, path in enumerate(input_paths):
        if cancel is not None and cancel.is_set():
            results.append(ToolResult(
                tool=ToolName.UNLOCK,
                input_paths=[path],
                success=False,
                message="Operation cancelled.",
            ))
            break

        pct = (idx / total) * 100
        _progress(f"Processing {path.name}", pct, idx + 1)

        if not path.is_file():
            results.append(ToolResult(
                tool=ToolName.UNLOCK,
                input_paths=[path],
                success=False,
                message=f"File not found: {path}",
            ))
            continue

        try:
            pdf = _open_pdf(path, password)

            if output_dir is None:
                out_dir = path.parent
            else:
                out_dir = output_dir
            out_dir.mkdir(parents=True, exist_ok=True)

            out_path = output_path_for(path, output_dir=out_dir, suffix=output_suffix)

            if remove_encryption or (new_permissions is None and not new_user_password and not new_owner_password):
                # Remove all encryption completely
                pdf.save(str(out_path), encryption=False)
                action_msg = "Restrictions and password removed"
            else:
                # Apply new permissions / passwords
                enc = pikepdf.Encryption(
                    owner=new_owner_password or "",
                    user=new_user_password,
                    allow=_to_pikepdf_permissions(
                        new_permissions or PdfPermissions(),
                    ),
                )
                pdf.save(str(out_path), encryption=enc)
                action_msg = "Permissions updated"

            output_size = out_path.stat().st_size
            page_count = len(pdf.pages)
            pdf.close()

            results.append(ToolResult(
                tool=ToolName.UNLOCK,
                input_paths=[path],
                output_path=out_path,
                success=True,
                message=f"{action_msg}: {path.name}",
                original_size=path.stat().st_size,
                output_size=output_size,
                page_count=page_count,
            ))

        except pikepdf.PasswordError:
            results.append(ToolResult(
                tool=ToolName.UNLOCK,
                input_paths=[path],
                success=False,
                message=f"Wrong password for {path.name}",
            ))
        except CancellationError:
            results.append(ToolResult(
                tool=ToolName.UNLOCK,
                input_paths=[path],
                success=False,
                message="Operation cancelled.",
            ))
            break
        except Exception as exc:
            logger.exception("Unlock failed for %s", path)
            results.append(ToolResult(
                tool=ToolName.UNLOCK,
                input_paths=[path],
                success=False,
                message=f"Failed: {exc}",
            ))

    _progress("Processing complete.", 100, total)
    return results


def _open_pdf(path: Path, password: str) -> pikepdf.Pdf:
    """Open a PDF, trying without password first then with."""
    try:
        return pikepdf.open(str(path))
    except pikepdf.PasswordError:
        if password:
            return pikepdf.open(str(path), password=password)
        raise
