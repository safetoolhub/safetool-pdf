# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for packaging/scripts/download_ghostscript.py.

The script now only supports Windows x64 (downloads the exe installer).
For Linux/macOS it exits gracefully with a message.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

import pytest

# Import the module under test
import importlib.util, sys

_script = Path(__file__).resolve().parent.parent / "packaging" / "scripts" / "download_ghostscript.py"
_spec = importlib.util.spec_from_file_location("download_ghostscript", _script)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
sys.modules["download_ghostscript"] = _mod
_spec.loader.exec_module(_mod)

# Re-export for readability
GS_VERSION = _mod.GS_VERSION
GS_VERSION_SHORT = _mod.GS_VERSION_SHORT
_BASE = _mod._BASE
_WINDOWS_URL = _mod._WINDOWS_URL


# ---------------------------------------------------------------------------
# Test: URL construction
# ---------------------------------------------------------------------------

class TestURLConstruction:
    """Verify that the constructed URLs follow the expected patterns."""

    def test_version_short_strips_dots(self) -> None:
        """GS_VERSION_SHORT should have no dots."""
        assert "." not in GS_VERSION_SHORT
        assert GS_VERSION_SHORT == GS_VERSION.replace(".", "")

    def test_base_url_contains_version(self) -> None:
        """The base URL must include the correct tag."""
        assert f"gs{GS_VERSION_SHORT}" in _BASE
        assert "github.com/ArtifexSoftware/ghostpdl-downloads" in _BASE

    def test_windows_url_is_exe_installer(self) -> None:
        """Windows URL must point to gs{SHORT}w64.exe."""
        expected_name = f"gs{GS_VERSION_SHORT}w64.exe"
        assert _WINDOWS_URL.endswith(expected_name)
        assert _WINDOWS_URL.startswith(_BASE)


# ---------------------------------------------------------------------------
# Test: URL reachability (HTTP HEAD check)
# ---------------------------------------------------------------------------

def _head_check(url: str) -> int:
    """Return the HTTP status code for a HEAD request, following redirects."""
    req = urllib.request.Request(url, method="HEAD")
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except Exception:
        pytest.skip(f"Network unavailable for {url}")
        return -1


class TestURLReachability:
    """Verify that the Windows download URL actually resolves (no 404)."""

    def test_windows_url_exists(self) -> None:
        """HEAD request to the Windows download URL should return 200 or 302."""
        status = _head_check(_WINDOWS_URL)
        assert status in (200, 302), (
            f"Windows URL returned HTTP {status}: {_WINDOWS_URL}"
        )


# ---------------------------------------------------------------------------
# Test: main() on non-Windows exits gracefully
# ---------------------------------------------------------------------------

class TestMainNonWindows:
    """On non-Windows platforms, main() should exit with code 0."""

    def test_exits_on_linux(self) -> None:
        with patch("platform.system", return_value="Linux"), \
             patch("struct.calcsize", return_value=8):
            with pytest.raises(SystemExit) as exc_info:
                _mod.main()
            assert exc_info.value.code == 0

    def test_exits_on_macos(self) -> None:
        with patch("platform.system", return_value="Darwin"), \
             patch("struct.calcsize", return_value=8):
            with pytest.raises(SystemExit) as exc_info:
                _mod.main()
            assert exc_info.value.code == 0
