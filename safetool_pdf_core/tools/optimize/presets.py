# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Factory functions for the four optimization presets."""

from __future__ import annotations

from safetool_pdf_core.models import (
    CleanupOptions,
    GhostscriptOptions,
    LosslessOptions,
    LossyImageOptions,
    OptimizeOptions,
    PreservationMode,
    PresetName,
)

def lossless(
    preservation: PreservationMode = PreservationMode.PRESERVE,
) -> OptimizeOptions:
    """Preset 1 — Sin pérdida (default)."""
    opts = OptimizeOptions(
        preset=PresetName.LOSSLESS,
        preservation=preservation,
        lossless=LosslessOptions(
            object_stream_mode=True,
            recompress_flate=True,
            decode_streams=True,
            remove_unreferenced=True,
            coalesce_streams=True,
            externalize_inline_images=True,
            linearize=False,
        ),
        lossy_images=LossyImageOptions(enabled=False),
        ghostscript=GhostscriptOptions(enabled=False),
        cleanup=cleanup_for(preservation),
    )
    return opts

def moderate(
    preservation: PreservationMode = PreservationMode.PRESERVE,
) -> OptimizeOptions:
    """Preset 2 — Moderate."""
    opts = OptimizeOptions(
        preset=PresetName.MODERATE,
        preservation=preservation,
        lossless=LosslessOptions(
            object_stream_mode=True,
            recompress_flate=True,
            decode_streams=True,
            remove_unreferenced=True,
            coalesce_streams=True,
            externalize_inline_images=True,
            linearize=False,
        ),
        lossy_images=LossyImageOptions(
            enabled=True,
            target_dpi=150,
            jpeg_quality=80,
            ccitt_bitonal=False,
        ),
        ghostscript=GhostscriptOptions(
            enabled=True,
            font_subsetting=True,
            full_rewrite=False,
        ),
        cleanup=cleanup_for(preservation),
    )
    return opts

def aggressive(
    preservation: PreservationMode = PreservationMode.SIMPLIFY,
) -> OptimizeOptions:
    """Preset 3 — Aggressive."""
    opts = OptimizeOptions(
        preset=PresetName.AGGRESSIVE,
        preservation=preservation,
        lossless=LosslessOptions(
            object_stream_mode=True,
            recompress_flate=True,
            decode_streams=True,
            remove_unreferenced=True,
            coalesce_streams=True,
            externalize_inline_images=True,
            linearize=False,
        ),
        lossy_images=LossyImageOptions(
            enabled=True,
            target_dpi=96,
            jpeg_quality=50,
            ccitt_bitonal=True,
        ),
        ghostscript=GhostscriptOptions(
            enabled=True,
            font_subsetting=True,
            full_rewrite=True,
            gs_settings="/ebook",
        ),
        cleanup=cleanup_for(PreservationMode.SIMPLIFY),
    )
    return opts

def custom() -> OptimizeOptions:
    """Preset 4 — Personalizado (all defaults, user will modify)."""
    return OptimizeOptions(preset=PresetName.CUSTOM)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def cleanup_for(mode: PreservationMode) -> CleanupOptions:
    """Return cleanup options matching the preservation mode."""
    if mode is PreservationMode.SIMPLIFY:
        return CleanupOptions(
            remove_metadata=True,
            remove_attachments=True,
            remove_javascript=True,
            remove_thumbnails=True,
            flatten_forms=True,
            flatten_layers=True,
            remove_accessibility_tags=True,
            remove_bookmarks=True,
            remove_links=False,  # kept by default even in simplify
            flatten_annotations=True,
        )
    return CleanupOptions()  # all False — preserve everything


# Backward-compat alias (deprecated)
_cleanup_for = cleanup_for


def preset_requires_gs(name: PresetName) -> bool:
    """Return ``True`` if the preset's default options use Ghostscript."""
    return name in {PresetName.MODERATE, PresetName.AGGRESSIVE}


def preset_by_name(name: PresetName) -> OptimizeOptions:
    """Return the default options for a given preset name."""
    factories = {
        PresetName.LOSSLESS: lossless,
        PresetName.MODERATE: moderate,
        PresetName.AGGRESSIVE: aggressive,
        PresetName.CUSTOM: custom,
    }
    return factories[name]()
