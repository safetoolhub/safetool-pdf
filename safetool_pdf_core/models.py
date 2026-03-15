# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Data models for analysis, optimization options, results, and progress."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class PresetName(enum.Enum):
    """Available optimization presets."""

    LOSSLESS = "lossless"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    CUSTOM = "custom"

class PreservationMode(enum.Enum):
    """How interactive features are treated."""

    PRESERVE = "preserve"
    SIMPLIFY = "simplify"

class ToolName(enum.Enum):
    """Available PDF tools."""

    OPTIMIZE = "optimize"
    MERGE = "merge"
    NUMBER = "number"
    STRIP_METADATA = "strip_metadata"
    UNLOCK = "unlock"

# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ImageInfo:
    """Summary of an embedded image."""

    index: int
    width: int
    height: int
    dpi: float
    colorspace: str
    bpc: int  # bits per component
    filter: str  # compression filter, e.g. "DCTDecode"
    size_bytes: int

@dataclass(frozen=True)
class FontInfo:
    """Summary of an embedded font."""

    name: str
    type: str  # e.g. "TrueType", "Type1"
    embedded: bool
    subset: bool

@dataclass
class AnalysisResult:
    """Full analysis of a PDF file."""

    path: Path
    file_size: int = 0
    page_count: int = 0
    pdf_version: str = ""

    # Content flags
    has_images: bool = False
    images: list[ImageInfo] = field(default_factory=list)
    total_image_bytes: int = 0
    has_fonts: bool = False
    fonts: list[FontInfo] = field(default_factory=list)
    has_forms: bool = False
    has_signatures: bool = False
    has_bookmarks: bool = False
    has_links: bool = False
    has_layers: bool = False
    has_javascript: bool = False
    has_attachments: bool = False
    has_thumbnails: bool = False
    has_annotations: bool = False
    has_accessibility_tags: bool = False
    has_metadata: bool = False

    # Structural
    is_encrypted: bool = False
    encryption_method: str = ""
    is_linearized: bool = False
    is_pdfa: bool = False
    pdfa_level: str = ""

    # Optimization estimate
    already_optimized: bool = False
    estimated_reduction_pct: float = 0.0

    # Warnings generated during analysis
    warnings: list[str] = field(default_factory=list)

# ---------------------------------------------------------------------------
# Optimization options
# ---------------------------------------------------------------------------

@dataclass
class LosslessOptions:
    """Options for the lossless (pikepdf) stage."""

    object_stream_mode: bool = True
    recompress_flate: bool = True
    decode_streams: bool = True
    remove_unreferenced: bool = True
    coalesce_streams: bool = True
    externalize_inline_images: bool = True
    linearize: bool = False

@dataclass
class LossyImageOptions:
    """Options for the lossy image (PyMuPDF) stage."""

    enabled: bool = False
    target_dpi: int = 150
    jpeg_quality: int = 80
    ccitt_bitonal: bool = False

@dataclass
class GhostscriptOptions:
    """Options for the Ghostscript stage."""

    enabled: bool = False
    font_subsetting: bool = False
    full_rewrite: bool = False
    gs_settings: str = "/ebook"  # /screen, /ebook, /printer, /prepress

@dataclass
class CleanupOptions:
    """Options for selective feature removal / flattening."""

    remove_metadata: bool = False
    remove_attachments: bool = False
    remove_javascript: bool = False
    remove_thumbnails: bool = False
    flatten_forms: bool = False
    flatten_layers: bool = False
    remove_accessibility_tags: bool = False
    remove_bookmarks: bool = False
    remove_links: bool = False
    flatten_annotations: bool = False

@dataclass
class OptimizeOptions:
    """Complete set of options for one optimization run."""

    preset: PresetName = PresetName.LOSSLESS
    preservation: PreservationMode = PreservationMode.PRESERVE
    lossless: LosslessOptions = field(default_factory=LosslessOptions)
    lossy_images: LossyImageOptions = field(default_factory=LossyImageOptions)
    ghostscript: GhostscriptOptions = field(default_factory=GhostscriptOptions)
    cleanup: CleanupOptions = field(default_factory=CleanupOptions)
    password: str | None = None
    output_suffix: str = ""

# ---------------------------------------------------------------------------
# PDF Permissions
# ---------------------------------------------------------------------------

@dataclass
class PdfPermissions:
    """Individual PDF permission flags (matches pikepdf.Permissions)."""

    print_lowres: bool = True
    print_highres: bool = True
    modify_other: bool = True
    extract: bool = True
    modify_annotation: bool = True
    fill_forms: bool = True
    accessibility: bool = True
    modify_assembly: bool = True

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

@dataclass
class OptimizeResult:
    """Result of a single file optimization."""

    input_path: Path
    output_path: Path
    original_size: int = 0
    optimized_size: int = 0
    reduction_bytes: int = 0
    reduction_pct: float = 0.0
    page_count: int = 0
    preset: PresetName | None = None
    warnings: list[str] = field(default_factory=list)
    skipped: bool = False
    skipped_reason: str = ""

@dataclass
class ToolResult:
    """Result of a non-optimization tool execution on a single file (or merge)."""

    tool: ToolName
    input_paths: list[Path] = field(default_factory=list)
    output_path: Path | None = None
    success: bool = True
    message: str = ""
    warnings: list[str] = field(default_factory=list)
    original_size: int = 0
    output_size: int = 0
    page_count: int = 0

# ---------------------------------------------------------------------------
# Progress
# ---------------------------------------------------------------------------

@dataclass
class ProgressInfo:
    """Progress information emitted during optimization."""

    stage: str = ""
    message: str = ""
    percent: float = 0.0  # 0.0 – 100.0
    file_index: int = 0  # for batch: current file (1-based)
    file_total: int = 1  # for batch: total files
