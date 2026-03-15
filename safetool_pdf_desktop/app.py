# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""QApplication setup, entry point, Design System styling, maximized window."""

from __future__ import annotations

import faulthandler
import logging
import sys
from pathlib import Path

faulthandler.enable()

# Configure logging based on user settings
def setup_logging() -> None:
    """Configure logging based on user preferences."""
    from safetool_pdf_desktop.settings import load_setting, ENABLE_LOGGING
    
    enable_logging = bool(load_setting(ENABLE_LOGGING, False))
    
    if enable_logging:
        # Create logs directory in user's home folder
        log_dir = Path.home() / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "safetool-pdf.log"
        
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            handlers=[
                logging.FileHandler(log_file, encoding="utf-8"),
                logging.StreamHandler(sys.stdout)
            ]
        )
        logging.info(f"Logging enabled. Log file: {log_file}")
    else:
        # Only log to console with WARNING level
        logging.basicConfig(
            level=logging.WARNING,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )

setup_logging()

from PySide6.QtWidgets import QApplication

from safetool_pdf_core.constants import APP_NAME, VERSION
from safetool_pdf_desktop.main_window import MainWindow
from safetool_pdf_desktop.settings import get_language
from safetool_pdf_desktop.styles.design_system import DesignSystem
from i18n import init_i18n

def main() -> int:
    """Launch the SafeTool PDF desktop application."""
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(VERSION)
    app.setOrganizationName("safetoolhub.org")

    # Force light theme regardless of system settings
    from PySide6.QtCore import Qt
    app.setStyle("Fusion")  # Use Fusion style for consistent appearance
    
    # Set light palette to override system dark mode
    from PySide6.QtGui import QPalette, QColor
    palette = QPalette()
    
    # Base colors for light theme
    palette.setColor(QPalette.ColorRole.Window, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(245, 245, 245))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.Text, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.ColorRole.Link, QColor(37, 99, 235))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(37, 99, 235))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    
    app.setPalette(palette)

    # Initialise i18n before any UI creation
    init_i18n(get_language())

    # Apply Design System global stylesheet
    app.setStyleSheet(DesignSystem.get_stylesheet())

    window = MainWindow()
    window.showMaximized()

    exit_code = app.exec()
    
    # Ensure window is deleted before app
    window.deleteLater()
    
    # Process remaining events to ensure cleanup
    app.processEvents()
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())
