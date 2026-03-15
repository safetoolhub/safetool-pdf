# Full app flow test with real window
import sys
sys.argv = ['test']

import os
os.environ['QT_QPA_PLATFORM'] = 'xcb'

from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import QTimer
app = QApplication.instance() or QApplication(sys.argv)

from i18n import init_i18n
from safetool_pdf_desktop.settings import get_language
init_i18n(get_language())

from safetool_pdf_desktop.main_window import MainWindow
from pathlib import Path

print("Creating MainWindow...")
win = MainWindow()
win.show()
print("MainWindow shown")

test_pdf = Path("/home/ed/HACK/safetool-pdf-dev/tests/test_pdfs/generated/large_images.pdf")
print(f"Using test PDF: {test_pdf} (exists: {test_pdf.exists()})")

def simulate_file_selection():
    print("Simulating file selection (calling _on_files_selected)...")
    win._on_files_selected([test_pdf])
    print("_on_files_selected called - workers should be running now")

def check_done():
    print("Checking status...")
    screen = win._strategy_screen
    stack_idx = screen._inner_stack.currentIndex()
    print(f"Inner stack index: {stack_idx} (0=analyzing, 1=comparison, 2=optimizing)")
    if stack_idx == 1:
        print("SUCCESS: Reached comparison page without crash!")
        app.quit()
    else:
        print("Still analyzing/estimating... checking again in 5s")
        QTimer.singleShot(5000, check_done)

# Simulate file selection after 500ms (window needs time to show)
QTimer.singleShot(500, simulate_file_selection)
# Check for completion every 5 seconds, starting after 5s
QTimer.singleShot(5000, check_done)
# Timeout after 120 seconds
QTimer.singleShot(120000, lambda: (print("TIMEOUT"), app.quit()))

print("Starting event loop...")
exit_code = app.exec()
print(f"Event loop finished with code: {exit_code}")
print("No segfault!" if exit_code == 0 else f"Exit code: {exit_code}")
