# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for safetool_pdf_core.models — dataclasses, enums, defaults."""

from __future__ import annotations

from pathlib import Path

import pytest

from safetool_pdf_core.models import (
    AnalysisResult,
    CleanupOptions,
    GhostscriptOptions,
    LosslessOptions,
    LossyImageOptions,
    OptimizeOptions,
    OptimizeResult,
    PreservationMode,
    PresetName,
    ProgressInfo,
)


class TestEnums:
    """Enum values and membership."""

    def test_preset_names(self) -> None:
        assert set(PresetName) == {
            PresetName.LOSSLESS,
            PresetName.MODERATE,
            PresetName.AGGRESSIVE,
            PresetName.CUSTOM,
        }

    def test_preset_values(self) -> None:
        assert PresetName.LOSSLESS.value == "lossless"
        assert PresetName.AGGRESSIVE.value == "aggressive"

    def test_preservation_modes(self) -> None:
        assert PreservationMode.PRESERVE.value == "preserve"
        assert PreservationMode.SIMPLIFY.value == "simplify"


class TestDefaults:
    """Default field values on dataclasses."""

    def test_lossless_defaults(self) -> None:
        opts = LosslessOptions()
        assert opts.object_stream_mode is True
        assert opts.recompress_flate is True
        assert opts.linearize is False

    def test_lossy_defaults(self) -> None:
        opts = LossyImageOptions()
        assert opts.enabled is False
        assert opts.target_dpi == 150
        assert opts.jpeg_quality == 80

    def test_gs_defaults(self) -> None:
        opts = GhostscriptOptions()
        assert opts.enabled is False
        assert opts.gs_settings == "/ebook"

    def test_cleanup_defaults(self) -> None:
        opts = CleanupOptions()
        assert opts.remove_metadata is False
        assert opts.flatten_forms is False
        assert opts.remove_javascript is False

    def test_optimize_options_defaults(self) -> None:
        opts = OptimizeOptions()
        assert opts.preset == PresetName.LOSSLESS
        assert opts.preservation == PreservationMode.PRESERVE
        assert opts.password is None

    def test_optimize_result_defaults(self) -> None:
        r = OptimizeResult(input_path=Path("/a.pdf"), output_path=Path("/b.pdf"))
        assert r.skipped is False
        assert r.skipped_reason == ""
        assert r.warnings == []
        assert r.reduction_pct == 0.0

    def test_progress_info_defaults(self) -> None:
        p = ProgressInfo()
        assert p.stage == ""
        assert p.percent == 0.0
        assert p.file_index == 0
        assert p.file_total == 1

    def test_analysis_result_defaults(self) -> None:
        a = AnalysisResult(path=Path("/test.pdf"))
        assert a.page_count == 0
        assert a.has_images is False
        assert a.is_encrypted is False
        assert a.warnings == []


class TestProgressInfo:
    """ProgressInfo mutation for batch processing."""

    def test_mutable_file_fields(self) -> None:
        p = ProgressInfo(stage="init", percent=10.0)
        p.file_index = 2
        p.file_total = 5
        assert p.file_index == 2
        assert p.file_total == 5


class TestExceptions:
    """Exception hierarchy."""

    def test_all_exceptions_subclass_base(self) -> None:
        from safetool_pdf_core.exceptions import (
            AnalysisError,
            CancellationError,
            EncryptedPDFError,
            GhostscriptError,
            GhostscriptNotFoundError,
            InvalidPDFError,
            OptimizationError,
            SafeToolPDFError,
            SignedPDFError,
            VerificationError,
        )

        for exc_class in [
            AnalysisError,
            CancellationError,
            EncryptedPDFError,
            GhostscriptError,
            GhostscriptNotFoundError,
            InvalidPDFError,
            OptimizationError,
            SignedPDFError,
            VerificationError,
        ]:
            assert issubclass(exc_class, SafeToolPDFError)

    def test_exceptions_carry_message(self) -> None:
        from safetool_pdf_core.exceptions import InvalidPDFError

        exc = InvalidPDFError("test message")
        assert str(exc) == "test message"
