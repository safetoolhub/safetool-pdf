# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Details Dialog — Professional PDF analysis information with extended data."""

from __future__ import annotations

import datetime
import logging
import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from safetool_pdf_core.models import AnalysisResult
from safetool_pdf_desktop.dialogs.base_dialog import BaseDialog
from safetool_pdf_desktop.styles.design_system import DesignSystem
from safetool_pdf_desktop.styles.icons import icon_manager
from i18n import tr

_logger = logging.getLogger(__name__)


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def _format_date(ts: float | None) -> str:
    if ts is None:
        return "N/A"
    try:
        return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except (OSError, ValueError):
        return "N/A"


def _gather_extended_info(path: Path) -> dict:
    """Gather extra PDF metadata not in AnalysisResult (live from file)."""
    _logger.info(f"Gathering extended info for: {path}")
    info: dict = {}
    # File system info
    try:
        stat = path.stat()
        info["created"] = _format_date(getattr(stat, "st_birthtime", stat.st_ctime))
        info["modified"] = _format_date(stat.st_mtime)
        info["permissions"] = oct(stat.st_mode)[-3:]
        _logger.debug(f"File system info gathered successfully")
    except OSError as exc:
        _logger.warning(f"Failed to get file system info: {exc}")
        info["created"] = "N/A"
        info["modified"] = "N/A"
        info["permissions"] = "N/A"

    # PyMuPDF metadata
    try:
        import fitz
        _logger.debug(f"Opening PDF with PyMuPDF: {path}")
        doc = fitz.open(str(path))
        try:
            _logger.debug(f"PyMuPDF opened successfully. needs_pass={doc.needs_pass}, is_encrypted={doc.is_encrypted}")
            meta = doc.metadata or {}
            info["title"] = meta.get("title", "") or "—"
            info["author"] = meta.get("author", "") or "—"
            info["subject"] = meta.get("subject", "") or "—"
            info["keywords"] = meta.get("keywords", "") or "—"
            info["creator"] = meta.get("creator", "") or "—"
            info["producer"] = meta.get("producer", "") or "—"
            info["creation_date"] = meta.get("creationDate", "") or "—"
            info["mod_date"] = meta.get("modDate", "") or "—"

            # Page dimensions (first page)
            if doc.page_count > 0:
                page = doc.load_page(0)
                rect = page.rect
                w_in = rect.width / 72
                h_in = rect.height / 72
                w_cm = w_in * 2.54
                h_cm = h_in * 2.54
                info["page_size"] = (
                    f"{rect.width:.0f} × {rect.height:.0f} pt"
                    f"  ({w_in:.2f} × {h_in:.2f} in"
                    f"  /  {w_cm:.1f} × {h_cm:.1f} cm)"
                )
                # Detect standard sizes
                std = _detect_paper_size(rect.width, rect.height)
                if std:
                    info["page_size"] = f"{std}  —  {info['page_size']}"
                info["page_rotation"] = f"{page.rotation}°"
            else:
                info["page_size"] = "N/A"
                info["page_rotation"] = "N/A"

            # Encryption details
            # Use needs_pass as primary indicator, as is_encrypted may be False
            # even for encrypted PDFs when opened without password
            info["needs_password"] = doc.needs_pass
            info["is_encrypted"] = doc.needs_pass or doc.is_encrypted
            _logger.debug(f"Encryption status: needs_password={info['needs_password']}, is_encrypted={info['is_encrypted']}")
            encrypt_info = doc.get_page_labels()  # noqa — trigger internal read

            # Object count (approximate)
            info["xref_count"] = doc.xref_length()
            _logger.debug(f"PyMuPDF metadata extraction completed")
        finally:
            doc.close()
    except Exception as exc:
        _logger.error(f"Extended metadata extraction failed: {exc}", exc_info=True)


    # pikepdf encryption details
    try:
        import pikepdf
        _logger.debug(f"Opening PDF with pikepdf: {path}")
        pdf = pikepdf.open(str(path))
        try:
            info["pdf_pages_obj"] = len(pdf.pages)
            enc = pdf.encryption
            
            # Always try to get permissions if encryption object exists
            if enc:
                _logger.debug(f"pikepdf encryption object found")
                
                # Try to get encryption details
                try:
                    # Try both attribute and dictionary access
                    enc_v = None
                    if hasattr(enc, "V"):
                        enc_v = enc.V
                    elif hasattr(enc, "__getitem__"):
                        try:
                            enc_v = enc["V"]
                        except (KeyError, TypeError):
                            pass
                    
                    if enc_v is not None:
                        info["is_encrypted"] = True
                        info["enc_version"] = str(enc_v)
                        
                        # Try to get other encryption details
                        try:
                            info["enc_revision"] = str(enc.get("R", "—") if hasattr(enc, "get") else getattr(enc, "R", "—"))
                        except (KeyError, AttributeError):
                            info["enc_revision"] = "—"
                        
                        try:
                            info["enc_key_length"] = str(getattr(enc, "bits", "—"))
                        except AttributeError:
                            info["enc_key_length"] = "—"
                        
                        try:
                            info["enc_method"] = str(getattr(enc, "stream_method", "—"))
                        except AttributeError:
                            info["enc_method"] = "—"
                except Exception as e:
                    _logger.debug(f"Could not get encryption details: {e}")
                
                # Check if we have owner access (effective permissions)
                # pdf.owner_password_matched is True when:
                # - Opened with owner password, or
                # - No owner password is set (empty owner password)
                # In both cases, we have full access regardless of /P value
                has_owner_access = pdf.owner_password_matched
                info["has_owner_access"] = has_owner_access
                
                # Store /P value for technical display
                try:
                    info["enc_p_value"] = enc.P
                except (KeyError, AttributeError):
                    info["enc_p_value"] = None
                
                # Read permissions
                try:
                    # Always read stored permissions from pdf.allow
                    a = pdf.allow
                    stored_perms_dict = {
                        "print": a.print_lowres,
                        "modify": a.modify_other,
                        "extract": a.extract,
                        "annotate": a.modify_annotation,
                        "fill_forms": a.modify_form,
                        "extract_accessibility": a.accessibility,
                        "assemble": a.modify_assembly,
                        "print_high_quality": a.print_highres,
                    }
                    info["enc_stored_permissions"] = stored_perms_dict
                    
                    if has_owner_access:
                        # Owner access grants all permissions (effective)
                        perms_dict = {
                            "print": True,
                            "modify": True,
                            "extract": True,
                            "annotate": True,
                            "fill_forms": True,
                            "extract_accessibility": True,
                            "assemble": True,
                            "print_high_quality": True,
                        }
                        _logger.debug("Using effective permissions (owner access)")
                    else:
                        # Use stored permissions (user access)
                        perms_dict = stored_perms_dict
                        _logger.debug("Using stored permissions (user access)")
                    
                    info["enc_permissions"] = perms_dict
                    info["enc_permissions_summary"] = _format_permissions_summary(perms_dict)
                    _logger.debug(f"Permissions decoded: {perms_dict}")
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    _logger.debug(f"Failed to decode permissions: {e}")
                    info["enc_permissions"] = {}
                    info["enc_permissions_summary"] = "N/A"
            else:
                info["enc_version"] = "None"
                _logger.debug(f"pikepdf: No encryption object")
            _logger.debug(f"pikepdf metadata extraction completed")
        finally:
            pdf.close()
    except pikepdf.PasswordError as exc:
        # PDF is encrypted and we don't have the password
        info["is_encrypted"] = True
        info["needs_password"] = True
        _logger.warning(f"pikepdf: PDF is encrypted, password required: {exc}")
    except Exception as exc:
        _logger.error(f"pikepdf extended info failed: {exc}", exc_info=True)

    return info


def _detect_paper_size(w_pt: float, h_pt: float) -> str:
    """Detect common paper sizes from point dimensions."""
    # Normalize to portrait
    w, h = min(w_pt, h_pt), max(w_pt, h_pt)
    sizes = {
        "A4": (595, 842),
        "A3": (842, 1191),
        "A5": (420, 595),
        "Letter": (612, 792),
        "Legal": (612, 1008),
        "Tabloid": (792, 1224),
        "B5": (499, 709),
    }
    for name, (sw, sh) in sizes.items():
        if abs(w - sw) < 5 and abs(h - sh) < 5:
            return name
    return ""


def _decode_pdf_permissions(p_value: int) -> dict[str, bool]:
    """Decode the /P permissions integer into individual permission flags.
    
    Returns a dict with permission names as keys and boolean values.
    Based on PDF specification permission bits.
    """
    return {
        "print": bool(p_value & (1 << 2)),  # Bit 3
        "modify": bool(p_value & (1 << 3)),  # Bit 4
        "extract": bool(p_value & (1 << 4)),  # Bit 5 (copy/extract text)
        "annotate": bool(p_value & (1 << 5)),  # Bit 6 (add/modify annotations)
        "fill_forms": bool(p_value & (1 << 8)),  # Bit 9
        "extract_accessibility": bool(p_value & (1 << 9)),  # Bit 10
        "assemble": bool(p_value & (1 << 10)),  # Bit 11 (insert/rotate/delete pages)
        "print_high_quality": bool(p_value & (1 << 11)),  # Bit 12
    }


def _format_permissions_summary(perms: dict[str, bool]) -> str:
    """Format permissions dict as a comma-separated summary string."""
    allowed = []
    if perms.get("print"):
        allowed.append("Print")
    if perms.get("modify"):
        allowed.append("Modify")
    if perms.get("extract"):
        allowed.append("Copy text")
    if perms.get("annotate"):
        allowed.append("Add annotations")
    if perms.get("fill_forms"):
        allowed.append("Fill forms")
    if perms.get("extract_accessibility"):
        allowed.append("Accessibility extract")
    if perms.get("assemble"):
        allowed.append("Assemble")
    if perms.get("print_high_quality"):
        allowed.append("High-quality print")
    return ", ".join(allowed) if allowed else "None"


class DetailsDialog(BaseDialog):
    """Professional dialog showing comprehensive PDF analysis details."""

    def __init__(
        self,
        analysis: AnalysisResult,
        parent: QWidget | None = None,
    ) -> None:
        _logger.info(f"Creating DetailsDialog for: {analysis.path}")
        super().__init__(parent)
        self._analysis = analysis
        self._extended: dict = {}
        self.setWindowTitle(tr("details.window_title", filename=analysis.path.name))
        self.setMinimumSize(680, 520)
        self.resize(780, 680)
        try:
            _logger.debug("Calling _gather_extended_info...")
            self._extended = _gather_extended_info(analysis.path)
            _logger.debug(f"Extended info gathered: {self._extended.keys()}")
        except Exception as exc:
            _logger.error(f"Failed to gather extended info: {exc}", exc_info=True)
            self._extended = {}
        try:
            _logger.debug("Building UI...")
            self._build_ui()
            _logger.info("DetailsDialog created successfully")
        except Exception as exc:
            _logger.error(f"Failed to build UI: {exc}", exc_info=True)
            raise

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, DesignSystem.SPACE_12)
        layout.setSpacing(DesignSystem.SPACE_12)

        # ── Header card with gradient ──
        layout.addWidget(self._build_header())

        # Main content container with margins
        main_container = QWidget()
        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(
            DesignSystem.SPACE_16, 0,
            DesignSystem.SPACE_16, 0,
        )
        main_layout.setSpacing(DesignSystem.SPACE_12)
        layout.addWidget(main_container, 1)

        # ── Scrollable content ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(DesignSystem.get_scroll_area_style())

        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setSpacing(DesignSystem.SPACE_12)
        cl.setContentsMargins(0, 0, 0, 0)

        a = self._analysis
        ext = self._extended

        # ── File Information ──
        file_rows = [
            (tr("details.filename"), a.path.name),
            (tr("details.directory"), str(a.path.parent)),
            (tr("details.file_size"), f"{_format_size(a.file_size)}  ({a.file_size:,} bytes)"),
            (tr("details.pages"), str(a.page_count)),
            (tr("details.pdf_version"), a.pdf_version or "—"),
        ]
        if ext.get("page_size"):
            file_rows.append((tr("details.page_size"), ext["page_size"]))
        if ext.get("page_rotation"):
            file_rows.append((tr("details.page_rotation"), ext["page_rotation"]))
        file_rows.append((tr("details.created"), ext.get("created", tr("details.na"))))
        file_rows.append((tr("details.last_modified"), ext.get("modified", tr("details.na"))))
        if os.name != "nt":
            file_rows.append((tr("details.permissions"), ext.get("permissions", tr("details.na"))))
        if ext.get("xref_count"):
            file_rows.append((tr("details.internal_objects"), f"{ext['xref_count']:,}"))
        self._add_section(cl, "file-document", tr("details.file_information"), file_rows)

        # ── Document Metadata ──
        meta_rows = [
            (tr("details.title"), ext.get("title", "—")),
            (tr("details.author"), ext.get("author", "—")),
            (tr("details.subject"), ext.get("subject", "—")),
            (tr("details.keywords"), ext.get("keywords", "—")),
            (tr("details.creator"), ext.get("creator", "—")),
            (tr("details.producer"), ext.get("producer", "—")),
            (tr("details.pdf_creation_date"), ext.get("creation_date", "—")),
            (tr("details.pdf_modification_date"), ext.get("mod_date", "—")),
        ]
        self._add_section(cl, "information", tr("details.document_metadata"), meta_rows)

        # ── Security & Encryption ──
        sec_rows: list[tuple[str, str]] = []
        _logger.debug(f"Building security section: a.is_encrypted={a.is_encrypted}, ext.needs_password={ext.get('needs_password')}")
        
        # Check if encrypted from extended info (more reliable than analyzer)
        is_encrypted = ext.get("is_encrypted", a.is_encrypted)
        
        sec_rows.append((tr("details.encrypted"), tr("details.yes") if is_encrypted else tr("details.no")))
        if is_encrypted:
            sec_rows.append((tr("details.encryption_method"), a.encryption_method or tr("details.unknown")))
            if ext.get("enc_version") and ext["enc_version"] not in ("None", "—"):
                sec_rows.append((tr("details.encryption_version"), f"V={ext.get('enc_version', '—')}"))
                sec_rows.append((tr("details.encryption_revision"), f"R={ext.get('enc_revision', '—')}"))
                kl = ext.get("enc_key_length", "—")
                if kl and kl != "—":
                    sec_rows.append((tr("details.key_length"), f"{kl} bits"))
                if ext.get("enc_method", "—") not in ("—", ""):
                    sec_rows.append((tr("details.cipher_method"), ext.get("enc_method", "—")))
                # Show /P value (permissions integer)
                if ext.get("enc_p_value") is not None:
                    p_val = ext["enc_p_value"]
                    sec_rows.append((tr("details.permissions_value"), f"/P = {p_val}"))
            # Show password required if needs_password is set OR if encrypted
            if ext.get("needs_password") or is_encrypted:
                sec_rows.append((tr("details.password_required"), tr("details.yes")))
            else:
                sec_rows.append((tr("details.password_required"), tr("details.no")))
            # Show access level
            if ext.get("has_owner_access"):
                sec_rows.append((tr("details.access_level"), tr("details.owner_access")))
            else:
                sec_rows.append((tr("details.access_level"), tr("details.user_access")))
        else:
            sec_rows.append((tr("details.password_required"), tr("details.no")))
        sec_rows.append((tr("details.digital_signatures"), tr("details.yes") if a.has_signatures else tr("details.no")))
        sec_rows.append((tr("details.contains_javascript"), tr("details.yes") if a.has_javascript else tr("details.no")))
        self._add_section(cl, "lock", tr("details.security_encryption"), sec_rows)

        # ── PDF Permissions (detailed) ──
        # Show both stored and effective permissions when they differ
        perms = ext.get("enc_permissions", {})
        stored_perms = ext.get("enc_stored_permissions", {})
        has_owner_access = ext.get("has_owner_access", False)
        
        if isinstance(perms, dict) and perms:
            perm_rows = [
                (tr("details.perm_print"), tr("details.yes") if perms.get("print") else tr("details.no")),
                (tr("details.perm_print_high_quality"), tr("details.yes") if perms.get("print_high_quality") else tr("details.no")),
                (tr("details.perm_modify"), tr("details.yes") if perms.get("modify") else tr("details.no")),
                (tr("details.perm_extract"), tr("details.yes") if perms.get("extract") else tr("details.no")),
                (tr("details.perm_annotate"), tr("details.yes") if perms.get("annotate") else tr("details.no")),
                (tr("details.perm_fill_forms"), tr("details.yes") if perms.get("fill_forms") else tr("details.no")),
                (tr("details.perm_extract_accessibility"), tr("details.yes") if perms.get("extract_accessibility") else tr("details.no")),
                (tr("details.perm_assemble"), tr("details.yes") if perms.get("assemble") else tr("details.no")),
            ]
            
            # Add note if effective permissions differ from stored
            if has_owner_access and stored_perms and stored_perms != perms:
                perm_rows.insert(0, (tr("details.permissions_note"), tr("details.owner_access_note")))
        else:
            # No encryption = all permissions allowed
            yes = tr("details.yes")
            perm_rows = [
                (tr("details.perm_print"), yes),
                (tr("details.perm_print_high_quality"), yes),
                (tr("details.perm_modify"), yes),
                (tr("details.perm_extract"), yes),
                (tr("details.perm_annotate"), yes),
                (tr("details.perm_fill_forms"), yes),
                (tr("details.perm_extract_accessibility"), yes),
                (tr("details.perm_assemble"), yes),
            ]
        
        # Add section title based on access level
        if has_owner_access and is_encrypted:
            perm_title = tr("details.pdf_permissions_effective")
        else:
            perm_title = tr("details.pdf_permissions")
        
        self._add_section(cl, "shield-lock", perm_title, perm_rows)
        
        # ── PDF Permissions (stored) - only show if different from effective ──
        if has_owner_access and is_encrypted and stored_perms and stored_perms != perms:
            stored_perm_rows = [
                (tr("details.perm_print"), tr("details.yes") if stored_perms.get("print") else tr("details.no")),
                (tr("details.perm_print_high_quality"), tr("details.yes") if stored_perms.get("print_high_quality") else tr("details.no")),
                (tr("details.perm_modify"), tr("details.yes") if stored_perms.get("modify") else tr("details.no")),
                (tr("details.perm_extract"), tr("details.yes") if stored_perms.get("extract") else tr("details.no")),
                (tr("details.perm_annotate"), tr("details.yes") if stored_perms.get("annotate") else tr("details.no")),
                (tr("details.perm_fill_forms"), tr("details.yes") if stored_perms.get("fill_forms") else tr("details.no")),
                (tr("details.perm_extract_accessibility"), tr("details.yes") if stored_perms.get("extract_accessibility") else tr("details.no")),
                (tr("details.perm_assemble"), tr("details.yes") if stored_perms.get("assemble") else tr("details.no")),
            ]
            self._add_section(cl, "shield-lock-outline", tr("details.pdf_permissions_stored"), stored_perm_rows)

        # ── Structure & Compliance ──
        struct_rows = [
            (tr("details.linearized"), tr("details.yes") if a.is_linearized else tr("details.no")),
            (tr("details.pdfa_compliant"), tr("details.pdfa_yes", level=a.pdfa_level) if a.is_pdfa else tr("details.no")),
            (tr("details.accessibility_tags"), tr("details.yes") if a.has_accessibility_tags else tr("details.no")),
            (tr("details.already_optimized"), tr("details.yes") if a.already_optimized else tr("details.no")),
            (tr("details.estimated_reduction"), f"{a.estimated_reduction_pct:.1f}%"),
        ]
        self._add_section(cl, "shield-check", tr("details.structure_compliance"), struct_rows)

        # ── Content Features (with icons) ──
        feature_flags = [
            (a.has_images, tr("details.feature_images"), tr("details.feature_images_detail", count=len(a.images), size=_format_size(a.total_image_bytes))),
            (a.has_fonts, tr("details.feature_fonts"), tr("details.feature_fonts_detail", count=len(a.fonts))),
            (a.has_forms, tr("details.feature_forms"), ""),
            (a.has_signatures, tr("details.feature_signatures"), ""),
            (a.has_bookmarks, tr("details.feature_bookmarks"), ""),
            (a.has_links, tr("details.feature_links"), ""),
            (a.has_layers, tr("details.feature_layers"), ""),
            (a.has_javascript, tr("details.feature_javascript"), ""),
            (a.has_attachments, tr("details.feature_attachments"), ""),
            (a.has_thumbnails, tr("details.feature_thumbnails"), ""),
            (a.has_annotations, tr("details.feature_annotations"), ""),
            (a.has_accessibility_tags, tr("details.feature_accessibility"), ""),
            (a.has_metadata, tr("details.feature_metadata"), ""),
        ]
        self._add_features_section(cl, feature_flags)

        # ── Embedded Images (table) ──
        if a.images:
            self._add_image_table(cl, a.images)

        # ── Fonts (table) ──
        if a.fonts:
            self._add_font_table(cl, a.fonts)

        # ── Warnings ──
        if a.warnings:
            self._add_warnings_section(cl, a.warnings)

        cl.addStretch()
        scroll.setWidget(content)
        main_layout.addWidget(scroll, 1)

        # ── Close button ──
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton(tr("details.close"))
        icon_manager.set_button_icon(close_btn, "close-circle", size=16)
        close_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        close_btn.setMinimumWidth(120)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        main_layout.addLayout(btn_row)

    # ── Header ───────────────────────────────────────────────────────

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setStyleSheet(DesignSystem.get_details_header_style())
        hl = QHBoxLayout(header)
        hl.setSpacing(DesignSystem.SPACE_16)

        # Icon
        icon_lbl = QLabel()
        icon_manager.set_label_icon(
            icon_lbl, "magnify",
            color=DesignSystem.COLOR_PRIMARY, size=36,
        )
        hl.addWidget(icon_lbl)

        # Text block
        text_vl = QVBoxLayout()
        text_vl.setSpacing(DesignSystem.SPACE_2)

        title = QLabel(self._analysis.path.name)
        title.setStyleSheet(DesignSystem.get_details_header_title_style())
        text_vl.addWidget(title)

        a = self._analysis
        subtitle_parts = [
            tr("details.pages_subtitle", count=a.page_count),
            _format_size(a.file_size),
            f"v{a.pdf_version}" if a.pdf_version else None,
        ]
        subtitle = QLabel("  •  ".join(p for p in subtitle_parts if p))
        subtitle.setStyleSheet(DesignSystem.get_details_header_subtitle_style())
        text_vl.addWidget(subtitle)

        hl.addLayout(text_vl, 1)

        # Status badges
        badge_hl = QHBoxLayout()
        badge_hl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        badge_hl.setSpacing(DesignSystem.SPACE_4)
        if a.is_encrypted:
            badge_hl.addWidget(self._make_badge(
                tr("details.badge_encrypted"), DesignSystem.COLOR_DANGER_BG, DesignSystem.COLOR_DANGER,
            ))
        if a.has_signatures:
            badge_hl.addWidget(self._make_badge(
                tr("details.badge_signed"), DesignSystem.COLOR_SUCCESS_BG, DesignSystem.COLOR_SUCCESS,
            ))
        if a.is_pdfa:
            badge_hl.addWidget(self._make_badge(
                tr("details.badge_pdfa", level=a.pdfa_level), DesignSystem.COLOR_INFO_BG, DesignSystem.COLOR_INFO_TEXT,
            ))
        if a.already_optimized:
            badge_hl.addWidget(self._make_badge(
                tr("details.badge_optimized"), DesignSystem.COLOR_SUCCESS_BG, DesignSystem.COLOR_SUCCESS,
            ))
        hl.addLayout(badge_hl)

        return header

    @staticmethod
    def _make_badge(text: str, bg: str, fg: str) -> QLabel:
        badge = QLabel(text)
        badge.setStyleSheet(DesignSystem.get_details_badge_style(bg, fg))
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return badge

    # ── Section card ─────────────────────────────────────────────────

    def _add_section(
        self,
        parent_layout: QVBoxLayout,
        icon_name: str,
        title: str,
        rows: list[tuple[str, str]],
    ) -> None:
        section = QFrame()
        section.setObjectName("detailsSection")
        section.setStyleSheet(DesignSystem.get_details_section_card_style())
        sl = QVBoxLayout(section)
        sl.setSpacing(DesignSystem.SPACE_8)

        # Title row with icon
        title_row = QHBoxLayout()
        title_row.setSpacing(DesignSystem.SPACE_8)
        icon_lbl = QLabel()
        icon_manager.set_label_icon(
            icon_lbl, icon_name, color=DesignSystem.COLOR_PRIMARY, size=18,
        )
        title_row.addWidget(icon_lbl)

        title_label = QLabel(title)
        title_label.setStyleSheet(DesignSystem.get_details_section_title_style())
        title_row.addWidget(title_label, 1)
        sl.addLayout(title_row)

        # Divider
        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(DesignSystem.get_details_divider_style())
        sl.addWidget(divider)

        # Key-value grid
        grid = QGridLayout()
        grid.setHorizontalSpacing(DesignSystem.SPACE_16)
        grid.setVerticalSpacing(DesignSystem.SPACE_4)
        grid.setColumnMinimumWidth(0, 170)

        for row_idx, (key, value) in enumerate(rows):
            key_label = QLabel(key)
            key_label.setStyleSheet(DesignSystem.get_details_key_style())
            key_label.setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            )
            grid.addWidget(key_label, row_idx, 0)

            val_label = QLabel(str(value))
            val_label.setStyleSheet(DesignSystem.get_details_value_style())
            val_label.setWordWrap(True)
            val_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse,
            )
            grid.addWidget(val_label, row_idx, 1)

        sl.addLayout(grid)
        parent_layout.addWidget(section)

    # ── Features section ─────────────────────────────────────────────

    def _add_features_section(
        self,
        parent_layout: QVBoxLayout,
        features: list[tuple[bool, str, str]],
    ) -> None:
        section = QFrame()
        section.setObjectName("detailsSection")
        section.setStyleSheet(DesignSystem.get_details_section_card_style())
        sl = QVBoxLayout(section)
        sl.setSpacing(DesignSystem.SPACE_6)

        title_row = QHBoxLayout()
        title_row.setSpacing(DesignSystem.SPACE_8)
        icon_lbl = QLabel()
        icon_manager.set_label_icon(
            icon_lbl, "magnify", color=DesignSystem.COLOR_PRIMARY, size=18,
        )
        title_row.addWidget(icon_lbl)
        title_label = QLabel(tr("details.content_features"))
        title_label.setStyleSheet(DesignSystem.get_details_section_title_style())
        title_row.addWidget(title_label, 1)
        sl.addLayout(title_row)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(DesignSystem.get_details_divider_style())
        sl.addWidget(divider)

        # Two-column grid of feature chips
        grid = QGridLayout()
        grid.setHorizontalSpacing(DesignSystem.SPACE_8)
        grid.setVerticalSpacing(DesignSystem.SPACE_4)

        for i, (present, label, detail) in enumerate(features):
            row_frame = QFrame()
            row_frame.setStyleSheet(DesignSystem.get_details_feature_row_style(present))
            rl = QHBoxLayout(row_frame)
            rl.setContentsMargins(4, 2, 4, 2)
            rl.setSpacing(DesignSystem.SPACE_6)

            icon_name = "check-circle" if present else "close-circle"
            color = DesignSystem.COLOR_SUCCESS if present else DesignSystem.COLOR_TEXT_SECONDARY
            ic = QLabel()
            icon_manager.set_label_icon(ic, icon_name, color=color, size=14)
            rl.addWidget(ic)

            text = label
            if detail and present:
                text = f"{label}  ({detail})"
            tl = QLabel(text)
            tl.setStyleSheet(
                f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
                f"color: {color};"
                f"border: none; background: transparent;"
            )
            rl.addWidget(tl, 1)

            col = i % 2
            row = i // 2
            grid.addWidget(row_frame, row, col)

        sl.addLayout(grid)
        parent_layout.addWidget(section)

    # ── Image table ──────────────────────────────────────────────────

    def _add_image_table(
        self,
        parent_layout: QVBoxLayout,
        images: list,
    ) -> None:
        section = QFrame()
        section.setObjectName("detailsSection")
        section.setStyleSheet(DesignSystem.get_details_section_card_style())
        sl = QVBoxLayout(section)
        sl.setSpacing(DesignSystem.SPACE_6)

        title_row = QHBoxLayout()
        title_row.setSpacing(DesignSystem.SPACE_8)
        ic = QLabel()
        icon_manager.set_label_icon(ic, "image", color=DesignSystem.COLOR_PRIMARY, size=18)
        title_row.addWidget(ic)
        title_label = QLabel(tr("details.embedded_images_title", count=len(images)))
        title_label.setStyleSheet(DesignSystem.get_details_section_title_style())
        title_row.addWidget(title_label, 1)
        sl.addLayout(title_row)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(DesignSystem.get_details_divider_style())
        sl.addWidget(divider)

        # Table header
        hdr = QHBoxLayout()
        hdr.setContentsMargins(4, 0, 4, 0)
        for text, stretch in [(tr("details.image_dimensions"), 2), (tr("details.image_dpi"), 1), (tr("details.image_colorspace"), 1), (tr("details.image_filter"), 1), (tr("details.image_size"), 1)]:
            lbl = QLabel(text)
            lbl.setStyleSheet(DesignSystem.get_details_image_table_header_style())
            hdr.addWidget(lbl, stretch)
        sl.addLayout(hdr)

        # Rows (limit 30)
        display_images = images[:30]
        for i, img in enumerate(display_images):
            row_frame = QFrame()
            row_frame.setStyleSheet(DesignSystem.get_details_image_row_style(i % 2 == 0))
            rl = QHBoxLayout(row_frame)
            rl.setContentsMargins(4, 2, 4, 2)
            rl.setSpacing(DesignSystem.SPACE_4)

            dim = QLabel(f"{img.width} × {img.height} px")
            dim.setStyleSheet(DesignSystem.get_details_mono_value_style())
            rl.addWidget(dim, 2)

            dpi = QLabel(f"{img.dpi:.0f}")
            dpi.setStyleSheet(DesignSystem.get_details_mono_value_style())
            rl.addWidget(dpi, 1)

            cs = QLabel(img.colorspace)
            cs.setStyleSheet(DesignSystem.get_details_value_style())
            rl.addWidget(cs, 1)

            flt = QLabel(str(img.filter) if img.filter else "—")
            flt.setStyleSheet(DesignSystem.get_details_value_style())
            rl.addWidget(flt, 1)

            sz = QLabel(_format_size(img.size_bytes))
            sz.setStyleSheet(DesignSystem.get_details_mono_value_style())
            rl.addWidget(sz, 1)

            sl.addWidget(row_frame)

        if len(images) > 30:
            more = QLabel(tr("details.image_more", count=len(images) - 30))
            more.setStyleSheet(
                f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
                f"color: {DesignSystem.COLOR_TEXT_SECONDARY};"
                f"font-style: italic;"
                f"border: none; background: transparent;"
                f"padding: {DesignSystem.SPACE_4}px;"
            )
            more.setAlignment(Qt.AlignmentFlag.AlignCenter)
            sl.addWidget(more)

        # Summary
        total_bytes = sum(img.size_bytes for img in images)
        avg_dpi = sum(img.dpi for img in images) / len(images) if images else 0
        summary = QLabel(
            tr("details.image_summary",
               size=_format_size(total_bytes),
               avg_dpi=f"{avg_dpi:.0f}",
               count=len(images))
        )
        summary.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_XS}px;"
            f"color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f"font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};"
            f"border: none; background: transparent;"
            f"padding-top: {DesignSystem.SPACE_4}px;"
        )
        sl.addWidget(summary)
        parent_layout.addWidget(section)

    # ── Font table ───────────────────────────────────────────────────

    def _add_font_table(
        self,
        parent_layout: QVBoxLayout,
        fonts: list,
    ) -> None:
        section = QFrame()
        section.setObjectName("detailsSection")
        section.setStyleSheet(DesignSystem.get_details_section_card_style())
        sl = QVBoxLayout(section)
        sl.setSpacing(DesignSystem.SPACE_6)

        title_row = QHBoxLayout()
        title_row.setSpacing(DesignSystem.SPACE_8)
        ic = QLabel()
        icon_manager.set_label_icon(ic, "file-document", color=DesignSystem.COLOR_PRIMARY, size=18)
        title_row.addWidget(ic)
        title_label = QLabel(tr("details.fonts_title", count=len(fonts)))
        title_label.setStyleSheet(DesignSystem.get_details_section_title_style())
        title_row.addWidget(title_label, 1)
        sl.addLayout(title_row)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(DesignSystem.get_details_divider_style())
        sl.addWidget(divider)

        # Table header
        hdr = QHBoxLayout()
        hdr.setContentsMargins(4, 0, 4, 0)
        for text, stretch in [(tr("details.font_name"), 3), (tr("details.font_type"), 1), (tr("details.font_embedded"), 1), (tr("details.font_subset"), 1)]:
            lbl = QLabel(text)
            lbl.setStyleSheet(DesignSystem.get_details_image_table_header_style())
            hdr.addWidget(lbl, stretch)
        sl.addLayout(hdr)

        for i, font in enumerate(fonts):
            row_frame = QFrame()
            row_frame.setStyleSheet(DesignSystem.get_details_image_row_style(i % 2 == 0))
            rl = QHBoxLayout(row_frame)
            rl.setContentsMargins(4, 2, 4, 2)
            rl.setSpacing(DesignSystem.SPACE_4)

            name_lbl = QLabel(font.name)
            name_lbl.setStyleSheet(DesignSystem.get_details_value_style())
            name_lbl.setToolTip(font.name)
            rl.addWidget(name_lbl, 3)

            type_lbl = QLabel(font.type)
            type_lbl.setStyleSheet(DesignSystem.get_details_value_style())
            rl.addWidget(type_lbl, 1)

            emb_color = DesignSystem.COLOR_SUCCESS if font.embedded else DesignSystem.COLOR_DANGER
            emb_lbl = QLabel(tr("details.yes") if font.embedded else tr("details.no"))
            emb_lbl.setStyleSheet(
                f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
                f"color: {emb_color};"
                f"font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};"
                f"border: none; background: transparent;"
            )
            rl.addWidget(emb_lbl, 1)

            sub_color = DesignSystem.COLOR_SUCCESS if font.subset else DesignSystem.COLOR_TEXT_SECONDARY
            sub_lbl = QLabel(tr("details.yes") if font.subset else tr("details.no"))
            sub_lbl.setStyleSheet(
                f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
                f"color: {sub_color};"
                f"border: none; background: transparent;"
            )
            rl.addWidget(sub_lbl, 1)

            sl.addWidget(row_frame)

        # Summary
        embedded_count = sum(1 for f in fonts if f.embedded)
        subset_count = sum(1 for f in fonts if f.subset)
        summary = QLabel(
            tr("details.font_summary",
               embedded=embedded_count, total=len(fonts),
               subset=subset_count)
        )
        summary.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_XS}px;"
            f"color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f"font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};"
            f"border: none; background: transparent;"
            f"padding-top: {DesignSystem.SPACE_4}px;"
        )
        sl.addWidget(summary)
        parent_layout.addWidget(section)

    # ── Warnings ─────────────────────────────────────────────────────

    def _add_warnings_section(
        self,
        parent_layout: QVBoxLayout,
        warnings: list[str],
    ) -> None:
        section = QFrame()
        section.setStyleSheet(DesignSystem.get_details_warning_style())
        sl = QVBoxLayout(section)
        sl.setSpacing(DesignSystem.SPACE_6)

        title_row = QHBoxLayout()
        title_row.setSpacing(DesignSystem.SPACE_8)
        ic = QLabel()
        icon_manager.set_label_icon(
            ic, "information", color=DesignSystem.COLOR_WARNING, size=18,
        )
        title_row.addWidget(ic)
        title_label = QLabel(tr("details.warnings_title"))
        title_label.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_BASE}px;"
            f"font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
            f"color: {DesignSystem.COLOR_TEXT};"
            f"border: none; background: transparent;"
        )
        title_row.addWidget(title_label, 1)
        sl.addLayout(title_row)

        for w in warnings:
            wl = QLabel(f"• {w}")
            wl.setStyleSheet(
                f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
                f"color: {DesignSystem.COLOR_TEXT};"
                f"border: none; background: transparent;"
            )
            wl.setWordWrap(True)
            sl.addWidget(wl)

        parent_layout.addWidget(section)
