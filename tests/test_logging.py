# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for logging configuration based on user settings."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


class TestLoggingConfiguration:
    """Tests for logging setup based on ENABLE_LOGGING setting."""

    def test_logging_disabled_by_default(self, tmp_path: Path) -> None:
        """When ENABLE_LOGGING is False, logs should not be saved to file."""
        # Mock the settings to return False
        with patch("safetool_pdf_desktop.settings.load_setting", return_value=False):
            # Clear any existing handlers
            logging.root.handlers.clear()
            
            # Import and run setup_logging
            from safetool_pdf_desktop.app import setup_logging
            setup_logging()
            
            # Check that no FileHandler is present
            file_handlers = [
                h for h in logging.root.handlers 
                if isinstance(h, logging.FileHandler)
            ]
            assert len(file_handlers) == 0, "No file handler should be present when logging is disabled"
            
            # Check that logging level is WARNING
            assert logging.root.level == logging.WARNING

    def test_logging_enabled_creates_file(self, tmp_path: Path) -> None:
        """When ENABLE_LOGGING is True, logs should be saved to file."""
        log_dir = tmp_path / "logs"
        log_file = log_dir / "safetool-pdf.log"
        
        # Mock Path.home() to use tmp_path
        with patch("pathlib.Path.home", return_value=tmp_path):
            with patch("safetool_pdf_desktop.settings.load_setting", return_value=True):
                # Clear any existing handlers
                logging.root.handlers.clear()
                
                # Import and run setup_logging
                from safetool_pdf_desktop.app import setup_logging
                setup_logging()
                
                # Check that FileHandler is present
                file_handlers = [
                    h for h in logging.root.handlers 
                    if isinstance(h, logging.FileHandler)
                ]
                assert len(file_handlers) > 0, "File handler should be present when logging is enabled"
                
                # Check that logging level is DEBUG
                assert logging.root.level == logging.DEBUG
                
                # Check that log directory was created
                assert log_dir.exists(), "Log directory should be created"
                
                # Write a test log message
                logger = logging.getLogger("test_logger")
                logger.info("Test log message")
                
                # Force flush handlers
                for handler in logging.root.handlers:
                    handler.flush()
                
                # Check that log file exists and contains the message
                assert log_file.exists(), "Log file should be created"
                log_content = log_file.read_text(encoding="utf-8")
                assert "Test log message" in log_content, "Log file should contain the test message"

    def test_logging_enabled_has_both_handlers(self, tmp_path: Path) -> None:
        """When logging is enabled, both file and console handlers should be present."""
        with patch("pathlib.Path.home", return_value=tmp_path):
            with patch("safetool_pdf_desktop.settings.load_setting", return_value=True):
                # Clear any existing handlers
                logging.root.handlers.clear()
                
                # Import and run setup_logging
                from safetool_pdf_desktop.app import setup_logging
                setup_logging()
                
                # Check for FileHandler
                file_handlers = [
                    h for h in logging.root.handlers 
                    if isinstance(h, logging.FileHandler)
                ]
                assert len(file_handlers) > 0, "Should have at least one FileHandler"
                
                # Check for StreamHandler
                stream_handlers = [
                    h for h in logging.root.handlers 
                    if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
                ]
                assert len(stream_handlers) > 0, "Should have at least one StreamHandler"

    def test_log_file_location(self, tmp_path: Path) -> None:
        """Verify that log file is created in the correct location."""
        expected_log_dir = tmp_path / "logs"
        expected_log_file = expected_log_dir / "safetool-pdf.log"
        
        with patch("pathlib.Path.home", return_value=tmp_path):
            with patch("safetool_pdf_desktop.settings.load_setting", return_value=True):
                # Clear any existing handlers
                logging.root.handlers.clear()
                
                # Import and run setup_logging
                from safetool_pdf_desktop.app import setup_logging
                setup_logging()
                
                # Write a log message to ensure file is created
                logger = logging.getLogger("location_test")
                logger.debug("Location test message")
                
                # Force flush
                for handler in logging.root.handlers:
                    handler.flush()
                
                # Verify location
                assert expected_log_dir.exists(), f"Log directory should exist at {expected_log_dir}"
                assert expected_log_file.exists(), f"Log file should exist at {expected_log_file}"

    def test_logging_format(self, tmp_path: Path) -> None:
        """Verify that log messages have the correct format."""
        log_file = tmp_path / "logs" / "safetool-pdf.log"
        
        with patch("pathlib.Path.home", return_value=tmp_path):
            with patch("safetool_pdf_desktop.settings.load_setting", return_value=True):
                # Clear any existing handlers
                logging.root.handlers.clear()
                
                # Import and run setup_logging
                from safetool_pdf_desktop.app import setup_logging
                setup_logging()
                
                # Write a test log message
                logger = logging.getLogger("format_test")
                logger.warning("Format test message")
                
                # Force flush
                for handler in logging.root.handlers:
                    handler.flush()
                
                # Read log content
                log_content = log_file.read_text(encoding="utf-8")
                
                # Check format: should contain timestamp, level, logger name, and message
                assert "[WARNING]" in log_content, "Log should contain level"
                assert "format_test" in log_content, "Log should contain logger name"
                assert "Format test message" in log_content, "Log should contain message"
                # Check for timestamp pattern (YYYY-MM-DD HH:MM:SS)
                import re
                timestamp_pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"
                assert re.search(timestamp_pattern, log_content), "Log should contain timestamp"
