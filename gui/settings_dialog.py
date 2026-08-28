"""SettingsDialog — first-run setup and ongoing path configuration.

Qt concepts used here:
  - QDialog (modal child window)
  - QDialogButtonBox (standard OK / Cancel with platform-correct order)
  - QFileDialog.getOpenFileName (native OS file picker)
  - QSettings (key-value store persisted to the registry on Windows;
               no file to manage, survives app restarts automatically)
  - Custom composite widget (PathField) reused three times
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QWidget,
    QLineEdit, QPushButton, QHBoxLayout, QLabel,
    QFileDialog, QDialogButtonBox
)
from PySide6.QtCore import QSettings, Qt


class PathField(QWidget):
    """A text field paired with a Browse… button for selecting a file path."""

    def __init__(self, filter_str: str = "All Files (*)", parent=None):
        super().__init__(parent)
        self._filter = filter_str

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        self._edit = QLineEdit()
        self._btn  = QPushButton("Browse…")
        self._btn.setFixedWidth(80)
        self._btn.clicked.connect(self._browse)

        row.addWidget(self._edit)
        row.addWidget(self._btn)

    def _browse(self):
        # QFileDialog.getOpenFileName returns (path, selected_filter)
        # The second return value is the filter string that was active — we discard it.
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select file",
            self._edit.text() or "",  # start in the current directory if set
            self._filter
        )
        if path:
            self._edit.setText(path)

    # Expose text/setText so the dialog can treat PathField like a QLineEdit
    def text(self) -> str:
        return self._edit.text().strip()

    def setText(self, value: str):
        self._edit.setText(value)


class SettingsDialog(QDialog):
    """
    Four-path configuration dialog.

    Paths stored in QSettings:
      paths/vanilla_strings   — extracted vanilla SeventySix_en.strings
      paths/rules_json        — tidy_wasteland_analysis.json
      paths/custom_rules      — custom_rules.json  (may not exist yet)
      paths/compiled_output   — destination .STRINGS file written to the game folder
    """

    def __init__(self, parent=None, first_run: bool = False):
        super().__init__(parent)
        self.setWindowTitle("Settings" if not first_run else "First-Run Setup")
        self.setMinimumWidth(540)
        self.setModal(True)

        self._settings = QSettings()
        self._build_ui(first_run)
        self._load_saved_values()

    def _build_ui(self, first_run: bool):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        if first_run:
            intro = QLabel(
                "<b>Welcome to FO76 Tag Customizer!</b><br><br>"
                "Point the app at your files to get started. "
                "You can change these any time via <i>File → Settings…</i>"
            )
            intro.setWordWrap(True)
            intro.setTextFormat(Qt.TextFormat.RichText)
            layout.addWidget(intro)

        # Form rows
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self._vanilla_field = PathField("STRINGS files (*.strings *.STRINGS);;All Files (*)")
        self._rules_field   = PathField("JSON files (*.json);;All Files (*)")
        self._custom_field  = PathField("JSON files (*.json);;All Files (*)")
        self._output_field  = PathField("STRINGS files (*.strings *.STRINGS);;All Files (*)")

        form.addRow("Vanilla strings:", self._vanilla_field)
        form.addRow("Rules JSON:", self._rules_field)
        form.addRow("Custom rules JSON:", self._custom_field)
        form.addRow("Game strings (output):", self._output_field)

        # Helper text
        note = QLabel(
            "<small>"
            "Vanilla strings — extracted from SeventySix - Localization.ba2 "
            "(CLI: <code>python run.py extract</code>)<br>"
            "Rules JSON — tidy_wasteland_analysis.json from the data/ folder<br>"
            "Custom rules — your personal overrides file (created if missing)<br>"
            "Game strings — the .STRINGS file in your FO76 Data\\strings\\ folder "
            "(overwritten on Compile &amp; Deploy)"
            "</small>"
        )
        note.setWordWrap(True)
        note.setTextFormat(Qt.TextFormat.RichText)
        note.setStyleSheet("color: #888; padding-top: 4px;")

        layout.addLayout(form)
        layout.addWidget(note)

        # Standard OK / Cancel buttons
        # QDialogButtonBox handles platform button order automatically (e.g. OK left on
        # Windows, right on macOS) — a small but appreciated native-feel detail.
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_saved_values(self):
        self._vanilla_field.setText(self._settings.value("paths/vanilla_strings", ""))
        self._rules_field.setText(self._settings.value("paths/rules_json", ""))
        self._custom_field.setText(self._settings.value("paths/custom_rules", ""))
        self._output_field.setText(self._settings.value("paths/compiled_output", ""))

    def _save_and_accept(self):
        self._settings.setValue("paths/vanilla_strings", self._vanilla_field.text())
        self._settings.setValue("paths/rules_json",      self._rules_field.text())
        self._settings.setValue("paths/custom_rules",    self._custom_field.text())
        self._settings.setValue("paths/compiled_output", self._output_field.text())
        self.accept()
