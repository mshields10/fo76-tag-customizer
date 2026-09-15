"""
FO76 Tag Customizer — GUI entry point.

Run this file directly to launch the desktop app:
    python app.py

The CLI (run.py) remains fully functional alongside the GUI.
"""
import sys
import os

# Add scripts/ to sys.path in development so the backend modules are importable.
# In a PyInstaller bundle all modules are already frozen — the insert is harmless
# but we skip it to avoid any path confusion.
if not hasattr(sys, '_MEIPASS'):
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts'))

from PySide6.QtWidgets import QApplication

from gui.utils import populate_default_settings
from gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("FO76 Tag Customizer")
    app.setApplicationDisplayName("FO76 Tag Customizer")
    app.setOrganizationName("fo76-tag-customizer")

    # Populate QSettings with smart defaults before opening the main window.
    # Existing user values are never overwritten — this only fills in blanks.
    populate_default_settings()

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
