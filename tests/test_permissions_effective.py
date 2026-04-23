# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for effective permissions (owner vs user access)."""

from __future__ import annotations

from pathlib import Path

import pikepdf
import pytest

from safetool_pdf_core.models import PdfPermissions
from safetool_pdf_core.tools.unlock import execute, read_permissions


@pytest.fixture
def pdf_with_user_password(tmp_path: Path) -> Path:
    """Create a PDF with both user and owner passwords and print restrictions."""
    pdf_path = tmp_path / "user_password.pdf"
    
    # Create a simple PDF
    pdf = pikepdf.new()
    pdf.add_blank_page(page_size=(595, 842))  # A4
    
    # Set permissions with user password
    perms = pikepdf.Permissions(
        print_lowres=False,
        print_highres=False,
        modify_other=True,
        extract=True,
        modify_annotation=True,
        modify_form=True,
        accessibility=True,
        modify_assembly=True,
    )
    
    enc = pikepdf.Encryption(
        owner='owner123',
        user='user123',
        allow=perms,
    )
    
    pdf.save(str(pdf_path), encryption=enc)
    return pdf_path


@pytest.fixture
def pdf_with_owner_only(tmp_path: Path) -> Path:
    """Create a PDF with only owner password (no user password) and print restrictions."""
    pdf_path = tmp_path / "owner_only.pdf"
    
    # Create a simple PDF
    pdf = pikepdf.new()
    pdf.add_blank_page(page_size=(595, 842))  # A4
    
    # Set permissions with owner password only
    perms = pikepdf.Permissions(
        print_lowres=False,
        print_highres=False,
        modify_other=True,
        extract=True,
        modify_annotation=True,
        modify_form=True,
        accessibility=True,
        modify_assembly=True,
    )
    
    enc = pikepdf.Encryption(
        owner='owner123',
        user='',  # No user password
        allow=perms,
    )
    
    pdf.save(str(pdf_path), encryption=enc)
    return pdf_path


def test_read_permissions_with_user_password(pdf_with_user_password: Path):
    """Test that user password shows restricted permissions."""
    perms = read_permissions(pdf_with_user_password, password='user123')
    
    # With user password, should see the restrictions
    assert perms.print_lowres is False
    assert perms.print_highres is False
    assert perms.modify_other is True
    assert perms.extract is True


def test_read_permissions_with_owner_password(pdf_with_user_password: Path):
    """Test that owner password shows full permissions."""
    perms = read_permissions(pdf_with_user_password, password='owner123')
    
    # With owner password, should have full access
    assert perms.print_lowres is True
    assert perms.print_highres is True
    assert perms.modify_other is True
    assert perms.extract is True


def test_read_permissions_owner_only_no_password(pdf_with_owner_only: Path):
    """Test that PDF with owner password can be opened without password but shows restrictions."""
    perms = read_permissions(pdf_with_owner_only)
    
    # Opening without password when owner password is set should show restrictions
    # (because we don't have owner access)
    assert perms.print_lowres is False
    assert perms.print_highres is False


def test_read_permissions_owner_only_with_password(pdf_with_owner_only: Path):
    """Test that PDF with owner password shows full permissions when opened with password."""
    perms = read_permissions(pdf_with_owner_only, password='owner123')
    
    # With owner password, should have full access
    assert perms.print_lowres is True
    assert perms.print_highres is True


def test_effective_permissions_after_unlock(pdf_with_user_password: Path, tmp_path: Path):
    """Test that unlocked PDF shows effective permissions (the reported bug).
    
    This is the core issue: after using unlock tool to remove restrictions,
    the PDF should show full permissions in the Details Dialog, matching
    the behavior of PDF readers like Okular.
    """
    # Unlock the PDF (remove all restrictions)
    results = execute(
        [pdf_with_user_password],
        password='user123',
        output_dir=tmp_path,
        output_suffix='_unlocked',
        remove_encryption=True,
    )
    
    assert results[0].success
    unlocked_path = results[0].output_path
    
    # Read permissions from unlocked file
    perms = read_permissions(unlocked_path)
    
    # Should show full permissions (owner access)
    # This matches how Okular and other PDF readers behave
    assert perms.print_lowres is True, "Unlocked PDF should allow low-res printing"
    assert perms.print_highres is True, "Unlocked PDF should allow high-res printing"
    assert perms.modify_other is True
    assert perms.extract is True


def test_effective_permissions_with_empty_owner_password(tmp_path: Path):
    """Test PDF with empty owner password shows full permissions.
    
    When a PDF has encryption but no owner password (empty string),
    opening it without password gives owner access, so all permissions
    should be granted.
    """
    pdf_path = tmp_path / "empty_owner.pdf"
    
    # Create PDF with empty owner password
    pdf = pikepdf.new()
    pdf.add_blank_page(page_size=(595, 842))
    
    perms = pikepdf.Permissions(
        print_lowres=False,
        print_highres=False,
        modify_other=True,
        extract=True,
        modify_annotation=True,
        modify_form=True,
        accessibility=True,
        modify_assembly=True,
    )
    
    enc = pikepdf.Encryption(
        owner='',  # Empty owner password
        user='',   # Empty user password
        allow=perms,
    )
    
    pdf.save(str(pdf_path), encryption=enc)
    
    # Read permissions without password
    perms_read = read_permissions(pdf_path)
    
    # Should have full access (owner access with empty password)
    assert perms_read.print_lowres is True
    assert perms_read.print_highres is True
