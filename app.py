"""
FO76 Tag Customizer — GUI entry point.

Run this file directly to launch the desktop app:
    python app.py

The CLI (run.py) remains fully functional alongside the GUI.
"""
import sys
import os

# Make scripts/ importable from every module in this process, including gui/ sub-modules.
# Must happen before any gui imports so widgets can reach the backend.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from gui.main_window import MainWindow


def main():
    # High-DPI is on by default in Qt 6; no extra flag needed.
    app = QApplication(sys.argv)
    app.setApplicationName("FO76 Tag Customizer")
    app.setApplicationDisplayName("FO76 Tag Customizer")
    app.setOrganizationName("fo76-tag-customizer")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
