"""SettingsDialog — first-run setup and ongoing path configuration.

Qt concepts used here:
  - QDialog (modal child window)
  - QDialogButtonBox (standard OK / Cancel with platform-correct order)
  - QFileDialog.getOpenFileName (native OS file picker)
  - QGroupBox: visually groups related form rows under a heading
  - QSettings (key-value store persisted to the registry on Windows;
               no file to manage, survives app restarts automatically)
  - Custom composite widget (PathField) reused throughout
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QGroupBox, QWidget,
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
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select file",
            self._edit.text() or "",
            self._filter
        )
        if path:
            self._edit.setText(path)

    def text(self) -> str:
        return self._edit.text().strip()

    def setText(self, value: str):
        self._edit.setText(value)


class SettingsDialog(QDialog):
    """
    Path configuration dialog, organised into two groups.

    Runtime paths (QSettings keys):
      paths/vanilla_strings   — extracted vanilla SeventySix_en.strings
      paths/custom_rules      — custom_rules.json  (may not exist yet)
      paths/compiled_output   — destination .STRINGS written to the game folder

    Game Update Sync:
      paths/ba2               — SeventySix - Localization.ba2

    Note: paths/rules_json is managed automatically by populate_default_settings()
    and is intentionally hidden from the user — it always points to the bundled asset.
    """

    def __init__(self, parent=None, first_run: bool = False):
        super().__init__(parent)
        self.setWindowTitle("Settings" if not first_run else "First-Run Setup")
        self.setMinimumWidth(560)
        self.setModal(True)

        self._settings = QSettings()
        self._build_ui(first_run)
        self._load_saved_values()

    def _build_ui(self, first_run: bool):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        if first_run:
            intro = QLabel(
                "<b>Welcome to FO76 Tag Customizer!</b><br><br>"
                "Point the app at your files to get started. "
                "You can change these any time via <i>File → Settings…</i>"
            )
            intro.setWordWrap(True)
            intro.setTextFormat(Qt.TextFormat.RichText)
            layout.addWidget(intro)

        # ---- Group 1: Runtime paths ----
        # QGroupBox draws a labelled border around a section of a form —
        # a lightweight way to visually separate two categories of settings.
        runtime_group = QGroupBox("Runtime paths")
        runtime_form  = QFormLayout(runtime_group)
        runtime_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        runtime_form.setHorizontalSpacing(12)
        runtime_form.setVerticalSpacing(8)

        self._vanilla_field = PathField("STRINGS files (*.strings *.STRINGS);;All Files (*)")
        self._custom_field  = PathField("JSON files (*.json);;All Files (*)")
        self._output_field  = PathField("STRINGS files (*.strings *.STRINGS);;All Files (*)")

        runtime_form.addRow("Vanilla strings:", self._vanilla_field)
        runtime_form.addRow("Custom rules JSON:", self._custom_field)
        runtime_form.addRow("Game strings (output):", self._output_field)

        runtime_note = QLabel(
            "<small>"
            "Vanilla strings — extracted from the BA2 via <i>File → Sync with Game Update…</i><br>"
            "Custom rules — your personal tag overrides (created automatically if missing)<br>"
            "Game strings — .STRINGS file in FO76 Data\\strings\\ (overwritten on Compile &amp; Deploy)"
            "</small>"
        )
        runtime_note.setWordWrap(True)
        runtime_note.setTextFormat(Qt.TextFormat.RichText)
        runtime_note.setStyleSheet("color: #888; margin-top: 4px;")
        runtime_form.addRow(runtime_note)

        layout.addWidget(runtime_group)

        # ---- Group 2: Game Update Sync ----
        baseline_group = QGroupBox("Game Update Sync  (File → Sync with Game Update…)")
        baseline_form  = QFormLayout(baseline_group)
        baseline_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        baseline_form.setHorizontalSpacing(12)
        baseline_form.setVerticalSpacing(8)

        self._ba2_field = PathField("BA2 archives (*.ba2);;All Files (*)")
        baseline_form.addRow("BA2 archive:", self._ba2_field)

        baseline_note = QLabel(
            "<small>"
            "BA2 archive — SeventySix - Localization.ba2 in your FO76 Data\\ folder.<br>"
            "After a game patch, use <i>File → Sync with Game Update…</i> to re-extract "
            "the vanilla string list.  Your existing tag rules are never overwritten."
            "</small>"
        )
        baseline_note.setWordWrap(True)
        baseline_note.setTextFormat(Qt.TextFormat.RichText)
        baseline_note.setStyleSheet("color: #888; margin-top: 4px;")
        baseline_form.addRow(baseline_note)

        layout.addWidget(baseline_group)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_saved_values(self):
        self._vanilla_field.setText(self._settings.value("paths/vanilla_strings", ""))
        self._custom_field.setText(self._settings.value("paths/custom_rules", ""))
        self._output_field.setText(self._settings.value("paths/compiled_output", ""))
        self._ba2_field.setText(self._settings.value("paths/ba2", ""))

    def _save_and_accept(self):
        self._settings.setValue("paths/vanilla_strings", self._vanilla_field.text())
        self._settings.setValue("paths/custom_rules",    self._custom_field.text())
        self._settings.setValue("paths/compiled_output", self._output_field.text())
        self._settings.setValue("paths/ba2",             self._ba2_field.text())
        self.accept()
