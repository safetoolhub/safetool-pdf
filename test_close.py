#!/usr/bin/env python3
"""Test script to verify application closes without segfault."""

import sys
import time
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from safetool_pdf_desktop.main_window import MainWindow
from safetool_pdf_desktop.styles.design_system import DesignSystem
from i18n import init_i18n

def test_close():
    """Test that the application closes cleanly."""
    print("Starting application...")
    app = QApplication(sys.argv)
    app.setApplicationName("SafeTool PDF Test")
    
    # Initialize i18n
    init_i18n("en")
    
    # Apply stylesheet
    app.setStyleSheet(DesignSystem.get_stylesheet())
    
    window = MainWindow()
    window.show()
    
    print("Application started. Will close in 2 seconds...")
    
    # Close after 2 seconds
    QTimer.singleShot(2000, window.close)
    
    # Quit after 3 seconds to ensure cleanup
    QTimer.singleShot(3000, app.quit)
    
    exit_code = app.exec()
    
    print("Application closed cleanly!")
    print(f"Exit code: {exit_code}")
    
    return exit_code

if __name__ == "__main__":
    sys.exit(test_close())
