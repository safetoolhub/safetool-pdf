# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for preservation / simplify modes."""

from __future__ import annotations

from safetool_pdf_core.models import PreservationMode
from safetool_pdf_core.tools.optimize.presets import lossless, aggressive

class TestPreservationModes:
    """Verify that PRESERVE keeps features and SIMPLIFY removes them."""

    def test_preserve_keeps_forms(self) -> None:
        opts = lossless(preservation=PreservationMode.PRESERVE)
        assert opts.cleanup.flatten_forms is False
        assert opts.cleanup.remove_metadata is False
        assert opts.cleanup.remove_javascript is False
        assert opts.cleanup.remove_attachments is False

    def test_simplify_removes_metadata(self) -> None:
        opts = lossless(preservation=PreservationMode.SIMPLIFY)
        assert opts.cleanup.remove_metadata is True
        assert opts.cleanup.remove_attachments is True
        assert opts.cleanup.remove_javascript is True

    def test_simplify_cleanup_options(self) -> None:
        """All simplify-mode cleanup flags should be set (except remove_links)."""
        opts = aggressive(preservation=PreservationMode.SIMPLIFY)
        c = opts.cleanup
        assert c.remove_metadata is True
        assert c.remove_attachments is True
        assert c.remove_javascript is True
        assert c.remove_thumbnails is True
        assert c.flatten_forms is True
        assert c.flatten_layers is True
        assert c.remove_accessibility_tags is True
        assert c.remove_bookmarks is True
        assert c.flatten_annotations is True
        # Links are kept by default even in simplify
        assert c.remove_links is False
