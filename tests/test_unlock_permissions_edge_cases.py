# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Test edge cases for unlock tool permissions handling.

Tests specific scenarios where users might set partial permissions
or modify specific permission combinations.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from safetool_pdf_core.models import PdfPermissions
from safetool_pdf_core.tools.unlock import execute, read_stored_permissions


class TestUnlockPermissionsEdgeCases:
    """Test edge cases for permission handling in unlock tool."""

    def test_enable_all_permissions_from_restricted(
        self, generated_pdfs: dict[str, Path], tmp_path: Path
    ) -> None:
        """Test enabling all permissions on a restricted PDF."""
        src = generated_pdfs["permissions_with_user_pw"]
        
        # Verify source has restricted permissions
        src_perms = read_stored_permissions(src, password="1234")
        assert src_perms.print_lowres is False
        assert src_perms.print_highres is False
        assert src_perms.modify_other is False
        assert src_perms.extract is True  # Only this and accessibility are True
        assert src_perms.accessibility is True
        
        # Enable all permissions
        new_perms = PdfPermissions(
            print_lowres=True,
            print_highres=True,
            modify_other=True,
            extract=True,
            modify_annotation=True,
            fill_forms=True,
            accessibility=True,
            modify_assembly=True,
        )
        
        results = execute(
            [src],
            password="1234",
            new_permissions=new_perms,
            output_dir=tmp_path,
        )
        
        assert len(results) == 1
        r = results[0]
        assert r.success is True
        assert r.output_path is not None
        
        # Verify all permissions are now enabled
        output_perms = read_stored_permissions(r.output_path)
        assert output_perms.print_lowres is True
        assert output_perms.print_highres is True
        assert output_perms.modify_other is True
        assert output_perms.extract is True
        assert output_perms.modify_annotation is True
        assert output_perms.fill_forms is True
        assert output_perms.accessibility is True
        assert output_perms.modify_assembly is True

    def test_enable_all_except_extract(
        self, generated_pdfs: dict[str, Path], tmp_path: Path
    ) -> None:
        """Test enabling all permissions except extract (user error scenario)."""
        src = generated_pdfs["permissions_with_user_pw"]
        
        # Enable all permissions EXCEPT extract
        new_perms = PdfPermissions(
            print_lowres=True,
            print_highres=True,
            modify_other=True,
            extract=False,  # User forgot to enable this
            modify_annotation=True,
            fill_forms=True,
            accessibility=True,
            modify_assembly=True,
        )
        
        results = execute(
            [src],
            password="1234",
            new_permissions=new_perms,
            output_dir=tmp_path,
        )
        
        assert len(results) == 1
        r = results[0]
        assert r.success is True
        
        # Verify extract is still disabled
        output_perms = read_stored_permissions(r.output_path)
        assert output_perms.print_lowres is True
        assert output_perms.print_highres is True
        assert output_perms.modify_other is True
        assert output_perms.extract is False  # Should remain False
        assert output_perms.modify_annotation is True
        assert output_perms.fill_forms is True
        assert output_perms.accessibility is True
        assert output_perms.modify_assembly is True

    def test_enable_all_except_modify_other(
        self, generated_pdfs: dict[str, Path], tmp_path: Path
    ) -> None:
        """Test enabling all permissions except modify_other (edit permission)."""
        src = generated_pdfs["permissions_with_user_pw"]
        
        # Enable all permissions EXCEPT modify_other
        new_perms = PdfPermissions(
            print_lowres=True,
            print_highres=True,
            modify_other=False,  # User forgot to enable this
            extract=True,
            modify_annotation=True,
            fill_forms=True,
            accessibility=True,
            modify_assembly=True,
        )
        
        results = execute(
            [src],
            password="1234",
            new_permissions=new_perms,
            output_dir=tmp_path,
        )
        
        assert len(results) == 1
        r = results[0]
        assert r.success is True
        
        # Verify modify_other is still disabled
        output_perms = read_stored_permissions(r.output_path)
        assert output_perms.print_lowres is True
        assert output_perms.print_highres is True
        assert output_perms.modify_other is False  # Should remain False
        assert output_perms.extract is True
        assert output_perms.modify_annotation is True
        assert output_perms.fill_forms is True
        assert output_perms.accessibility is True
        assert output_perms.modify_assembly is True

    def test_partial_permissions_combination(
        self, generated_pdfs: dict[str, Path], tmp_path: Path
    ) -> None:
        """Test setting a specific combination of permissions."""
        src = generated_pdfs["permissions_with_user_pw"]
        
        # Enable only print and extract, disable everything else
        new_perms = PdfPermissions(
            print_lowres=True,
            print_highres=True,
            modify_other=False,
            extract=True,
            modify_annotation=False,
            fill_forms=False,
            accessibility=True,  # Usually kept enabled for accessibility tools
            modify_assembly=False,
        )
        
        results = execute(
            [src],
            password="1234",
            new_permissions=new_perms,
            output_dir=tmp_path,
        )
        
        assert len(results) == 1
        r = results[0]
        assert r.success is True
        
        # Verify exact permission combination
        output_perms = read_stored_permissions(r.output_path)
        assert output_perms.print_lowres is True
        assert output_perms.print_highres is True
        assert output_perms.modify_other is False
        assert output_perms.extract is True
        assert output_perms.modify_annotation is False
        assert output_perms.fill_forms is False
        assert output_perms.accessibility is True
        assert output_perms.modify_assembly is False

    def test_toggle_single_permission(
        self, generated_pdfs: dict[str, Path], tmp_path: Path
    ) -> None:
        """Test toggling a single permission while keeping others unchanged."""
        src = generated_pdfs["permissions_with_user_pw"]
        
        # Read current permissions
        src_perms = read_stored_permissions(src, password="1234")
        
        # Toggle only the extract permission (from True to False)
        new_perms = PdfPermissions(
            print_lowres=src_perms.print_lowres,
            print_highres=src_perms.print_highres,
            modify_other=src_perms.modify_other,
            extract=False,  # Toggle this from True to False
            modify_annotation=src_perms.modify_annotation,
            fill_forms=src_perms.fill_forms,
            accessibility=src_perms.accessibility,
            modify_assembly=src_perms.modify_assembly,
        )
        
        results = execute(
            [src],
            password="1234",
            new_permissions=new_perms,
            output_dir=tmp_path,
        )
        
        assert len(results) == 1
        r = results[0]
        assert r.success is True
        
        # Verify only extract changed
        output_perms = read_stored_permissions(r.output_path)
        assert output_perms.print_lowres == src_perms.print_lowres
        assert output_perms.print_highres == src_perms.print_highres
        assert output_perms.modify_other == src_perms.modify_other
        assert output_perms.extract is False  # Changed
        assert output_perms.modify_annotation == src_perms.modify_annotation
        assert output_perms.fill_forms == src_perms.fill_forms
        assert output_perms.accessibility == src_perms.accessibility
        assert output_perms.modify_assembly == src_perms.modify_assembly

    def test_read_stored_permissions_vs_effective(
        self, generated_pdfs: dict[str, Path]
    ) -> None:
        """Test that read_stored_permissions returns actual stored values."""
        src = generated_pdfs["permissions_with_user_pw"]
        
        # Read with owner password (which grants full access)
        stored_perms = read_stored_permissions(src, password="1234")
        
        # Should return the actual stored restrictions, not effective permissions
        assert stored_perms.print_lowres is False
        assert stored_perms.print_highres is False
        assert stored_perms.modify_other is False
        assert stored_perms.extract is True
        assert stored_perms.modify_annotation is False
        assert stored_perms.fill_forms is False
        assert stored_perms.accessibility is True
        assert stored_perms.modify_assembly is False

    def test_permissions_preserved_across_operations(
        self, generated_pdfs: dict[str, Path], tmp_path: Path
    ) -> None:
        """Test that permissions are correctly preserved through multiple operations."""
        src = generated_pdfs["permissions_with_user_pw"]
        
        # First operation: enable all permissions
        all_enabled = PdfPermissions(
            print_lowres=True,
            print_highres=True,
            modify_other=True,
            extract=True,
            modify_annotation=True,
            fill_forms=True,
            accessibility=True,
            modify_assembly=True,
        )
        
        results1 = execute(
            [src],
            password="1234",
            new_permissions=all_enabled,
            output_dir=tmp_path,
            output_suffix="_step1",
        )
        
        assert results1[0].success is True
        intermediate = results1[0].output_path
        
        # Second operation: disable extract on the intermediate file
        extract_disabled = PdfPermissions(
            print_lowres=True,
            print_highres=True,
            modify_other=True,
            extract=False,  # Disable this
            modify_annotation=True,
            fill_forms=True,
            accessibility=True,
            modify_assembly=True,
        )
        
        results2 = execute(
            [intermediate],
            new_permissions=extract_disabled,
            output_dir=tmp_path,
            output_suffix="_step2",
        )
        
        assert results2[0].success is True
        final = results2[0].output_path
        
        # Verify final permissions
        final_perms = read_stored_permissions(final)
        assert final_perms.print_lowres is True
        assert final_perms.print_highres is True
        assert final_perms.modify_other is True
        assert final_perms.extract is False  # Should be disabled
        assert final_perms.modify_annotation is True
        assert final_perms.fill_forms is True
        assert final_perms.accessibility is True
        assert final_perms.modify_assembly is True
