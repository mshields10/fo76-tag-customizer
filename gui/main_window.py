"""MainWindow — top-level application window.

Qt concepts used here:
  - QMainWindow: the frame that holds menus, toolbars, status bar, and a central widget
  - QTabWidget: multi-tab layout (Tab 1 = Tagger, Tab 2 = placeholder)
  - QAction + QMenuBar: File menu with Settings and Quit
  - QThread + worker QObject pattern: keeps the UI responsive during long operations
    (used for both the initial data load and the compile step)
  - QProgressBar in indeterminate mode: visual "working" indicator
  - QStatusBar: one-liner feedback at the bottom of the window
  - QSettings: reads the path config written by SettingsDialog
"""
import os
import json

from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QStatusBar, QMessageBox, QPushButton, QProgressBar,
    QCheckBox, QFrame
)
from PySide6.QtCore import Qt, QSettings, QThread, QObject, Signal
from PySide6.QtGui import QAction

from gui.settings_dialog import SettingsDialog
from gui.widgets.search_bar import SearchBar
from gui.widgets.tag_editor import TagEditor


# ---------------------------------------------------------------------------
# Background worker: initial data load
# ---------------------------------------------------------------------------

class _DataLoader(QObject):
    """
    Parses vanilla strings + rules JSON on a background thread.

    Emits finished(vanilla, sort_tiers, rules) or error(message).
    All three payloads are typed as `object` (not dict/list) so Shiboken
    passes them by reference instead of attempting a C++ copy-conversion.
    """
    finished = Signal(object, object, object)   # vanilla {int:str}, sort_tiers, rules list
    error    = Signal(str)

    def __init__(self, vanilla_path: str, rules_path: str):
        super().__init__()
        self._vanilla_path = vanilla_path
        self._rules_path   = rules_path

    def run(self):
        try:
            from parser import parse_strings_file
            vanilla = parse_strings_file(self._vanilla_path)

            with open(self._rules_path, encoding='utf-8') as f:
                data = json.load(f)
            sort_tiers = data.get('sort_tiers', {})
            rules      = data.get('rules', [])

            self.finished.emit(vanilla, sort_tiers, rules)
        except Exception as exc:
            self.error.emit(str(exc))


# ---------------------------------------------------------------------------
# Background worker: compile & deploy
# ---------------------------------------------------------------------------

class _CompileWorker(QObject):
    """
    Runs the full compile pipeline on a background thread so the UI stays
    responsive during the ~1-2 s it takes to apply 6k+ rules and write the
    binary.

    Progress messages are emitted as strings and shown in the status bar.
    """
    progress = Signal(str)
    finished = Signal(int, int)   # num_entries, data_size_bytes
    error    = Signal(str)

    def __init__(self, vanilla: dict, rules: list, sort_tiers: dict,
                 custom_rules_path: str, output_path: str, verify: bool):
        super().__init__()
        self._vanilla          = vanilla
        self._rules            = rules
        self._sort_tiers       = sort_tiers
        self._custom_rules_path = custom_rules_path
        self._output_path      = output_path
        self._verify           = verify

    def run(self):
        try:
            from compiler import merge_rules, build_modified_strings, write_strings_file, verify_output

            rules = self._rules

            # Merge in custom overrides if the file exists
            if self._custom_rules_path and os.path.exists(self._custom_rules_path):
                self.progress.emit("Loading custom rules…")
                with open(self._custom_rules_path, encoding='utf-8') as f:
                    data = json.load(f)
                custom_list = data.get('rules', [])
                rules = merge_rules(rules, custom_list)
                self.progress.emit(
                    f"Merged {len(custom_list)} custom rule(s)  ({len(rules):,} total)"
                )

            self.progress.emit(f"Applying {len(rules):,} rules…")
            modified, stats = build_modified_strings(self._vanilla, rules, self._sort_tiers)

            # Ensure the output directory exists (game may not have a strings/ subfolder
            # if it was never modded before)
            out_dir = os.path.dirname(self._output_path)
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)

            self.progress.emit(f"Writing {os.path.basename(self._output_path)}…")
            num_entries, data_size = write_strings_file(modified, self._output_path)

            if self._verify:
                self.progress.emit("Verifying…")
                mismatches = verify_output(self._output_path, modified)
                if mismatches:
                    self.error.emit(
                        f"Verification failed: {len(mismatches)} mismatches.\n"
                        f"First: {mismatches[0][0]:#010x} expected {mismatches[0][1]!r}"
                    )
                    return

            self.finished.emit(num_entries, data_size)

        except Exception as exc:
            self.error.emit(str(exc))


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FO76 Tag Customizer")
        self.resize(860, 660)

        self._vanilla: dict    = {}
        self._sort_tiers: dict = {}
        self._rules: list      = []
        self._settings         = QSettings()

        # Thread refs kept on self so they aren't garbage-collected mid-run
        self._load_thread: QThread | None    = None
        self._compile_thread: QThread | None = None

        self._build_menu()
        self._build_ui()
        self._load_data()

    # ------------------------------------------------------------------
    # Menu bar
    # ------------------------------------------------------------------

    def _build_menu(self):
        file_menu = self.menuBar().addMenu("&File")

        settings_action = QAction("&Settings…", self)
        settings_action.setStatusTip("Configure file paths")
        settings_action.triggered.connect(self._open_settings)
        file_menu.addAction(settings_action)

        file_menu.addSeparator()

        quit_action = QAction("&Quit", self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

    # ------------------------------------------------------------------
    # Central widget
    # ------------------------------------------------------------------

    def _build_ui(self):
        # Root widget holds tabs on top + compile bar at the bottom,
        # both inside one vertical layout.
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.setCentralWidget(root)

        # ---- Tabs ----
        self._tabs = QTabWidget()
        root_layout.addWidget(self._tabs, stretch=1)

        # Tab 1: Tag Items
        tab1 = QWidget()
        t1_layout = QVBoxLayout(tab1)
        t1_layout.setContentsMargins(14, 14, 14, 14)
        t1_layout.setSpacing(0)

        self._search_bar = SearchBar()
        self._tag_editor = TagEditor({})
        self._tag_editor.setEnabled(False)

        self._search_bar.item_selected.connect(self._on_item_selected)
        self._tag_editor.rule_ready.connect(self._on_rule_ready)

        t1_layout.addWidget(self._search_bar)
        t1_layout.addWidget(self._tag_editor)
        t1_layout.addStretch()

        self._tabs.addTab(tab1, "🏷  Tag Items")

        # Tab 2: Tagged Items (placeholder)
        tab2 = QWidget()
        t2_layout = QVBoxLayout(tab2)
        placeholder = QLabel(
            "📋  Coming soon\n\n"
            "This tab will show all items that have already been tagged by sort tier,\n"
            "so you can browse and edit your custom rules."
        )
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("color: #666; font-size: 14px;")
        t2_layout.addWidget(placeholder)
        self._tabs.addTab(tab2, "📋  Tagged Items")

        # ---- Compile bar ----
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        root_layout.addWidget(sep)

        compile_bar = QWidget()
        compile_bar.setStyleSheet("background: transparent;")
        cb_layout = QHBoxLayout(compile_bar)
        cb_layout.setContentsMargins(14, 10, 14, 12)
        cb_layout.setSpacing(10)

        self._compile_btn = QPushButton("▶  Compile && Deploy")
        self._compile_btn.setMinimumHeight(36)
        self._compile_btn.setMinimumWidth(180)
        self._compile_btn.setEnabled(False)   # enabled once data is loaded
        self._compile_btn.setToolTip(
            "Apply all rules + custom overrides to the vanilla strings\n"
            "and write the result to your FO76 Data folder."
        )
        self._compile_btn.clicked.connect(self._on_compile_clicked)

        self._verify_check = QCheckBox("Verify after write")
        self._verify_check.setToolTip(
            "Re-parse the output file and confirm every entry matches — adds ~0.5 s"
        )

        # Indeterminate progress bar — shown only while compiling
        # setRange(0, 0) puts it in "busy" / marquee mode
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 0)
        self._progress_bar.setFixedHeight(6)
        self._progress_bar.hide()

        cb_layout.addWidget(self._compile_btn)
        cb_layout.addWidget(self._verify_check)
        cb_layout.addStretch()

        # Stack the progress bar in its own row below the button row
        compile_wrapper = QWidget()
        cw_layout = QVBoxLayout(compile_wrapper)
        cw_layout.setContentsMargins(0, 0, 0, 0)
        cw_layout.setSpacing(4)
        cw_layout.addWidget(compile_bar)
        cw_layout.addWidget(self._progress_bar)

        root_layout.addWidget(compile_wrapper)

        # Status bar
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Starting up…")

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_data(self):
        vanilla_path = self._settings.value("paths/vanilla_strings", "")
        rules_path   = self._settings.value("paths/rules_json", "")

        if not vanilla_path or not rules_path:
            self._open_settings(first_run=True)
            return

        for path in (vanilla_path, rules_path):
            if not os.path.exists(path):
                self.statusBar().showMessage(f"File not found: {path}")
                return

        self.statusBar().showMessage("Loading item data…")
        self._compile_btn.setEnabled(False)

        # QThread worker pattern — see _DataLoader docstring
        self._load_thread = QThread()
        loader = _DataLoader(vanilla_path, rules_path)
        loader.moveToThread(self._load_thread)

        self._load_thread.started.connect(loader.run)
        loader.finished.connect(self._on_data_loaded)
        loader.error.connect(self._on_data_error)
        loader.finished.connect(self._load_thread.quit)
        loader.error.connect(self._load_thread.quit)
        self._load_thread.finished.connect(self._load_thread.deleteLater)

        # Keep a reference so the loader isn't GC'd before the thread finishes
        self._loader = loader
        self._load_thread.start()

    # ------------------------------------------------------------------
    # Compile
    # ------------------------------------------------------------------

    def _on_compile_clicked(self):
        output_path       = self._settings.value("paths/compiled_output", "")
        custom_rules_path = self._settings.value("paths/custom_rules", "")

        if not output_path:
            QMessageBox.warning(
                self, "No output path",
                "Set the 'Game strings (output)' path in File → Settings… first."
            )
            return

        # Lock the UI while compiling
        self._compile_btn.setEnabled(False)
        self._progress_bar.show()
        self.statusBar().showMessage("Compiling…")

        self._compile_thread = QThread()
        worker = _CompileWorker(
            vanilla          = self._vanilla,
            rules            = self._rules,
            sort_tiers       = self._sort_tiers,
            custom_rules_path = custom_rules_path,
            output_path      = output_path,
            verify           = self._verify_check.isChecked(),
        )
        worker.moveToThread(self._compile_thread)

        self._compile_thread.started.connect(worker.run)
        worker.progress.connect(self._on_compile_progress)
        worker.finished.connect(self._on_compile_finished)
        worker.error.connect(self._on_compile_error)
        worker.finished.connect(self._compile_thread.quit)
        worker.error.connect(self._compile_thread.quit)
        self._compile_thread.finished.connect(self._compile_thread.deleteLater)

        self._compile_worker = worker   # prevent GC
        self._compile_thread.start()

    def _on_compile_progress(self, message: str):
        self.statusBar().showMessage(message)

    def _on_compile_finished(self, num_entries: int, data_size: int):
        self._progress_bar.hide()
        self._compile_btn.setEnabled(True)
        kb = data_size / 1024
        self.statusBar().showMessage(
            f"✓  Done — {num_entries:,} entries, {kb:,.1f} KB written"
        )

    def _on_compile_error(self, message: str):
        self._progress_bar.hide()
        self._compile_btn.setEnabled(True)
        self.statusBar().showMessage(f"Compile failed: {message}")
        QMessageBox.critical(self, "Compile failed", message)

    # ------------------------------------------------------------------
    # Data-loaded slot
    # ------------------------------------------------------------------

    def _on_data_loaded(self, vanilla: dict, sort_tiers: dict, rules: list):
        self._vanilla    = vanilla
        self._sort_tiers = sort_tiers
        self._rules      = rules
        self._search_bar.set_data(vanilla)
        self._tag_editor.set_sort_tiers(sort_tiers)
        self._compile_btn.setEnabled(True)
        self.statusBar().showMessage(
            f"Loaded {len(vanilla):,} items  •  {len(rules):,} rules  •  Ready"
        )

    def _on_data_error(self, message: str):
        self.statusBar().showMessage(f"Load error: {message}")
        QMessageBox.critical(self, "Could not load data", message)

    # ------------------------------------------------------------------
    # Tag editor slots
    # ------------------------------------------------------------------

    def _on_item_selected(self, form_id: int, name: str):
        self._tag_editor.set_item(form_id, name)
        self._tag_editor.setEnabled(True)

    def _on_rule_ready(self, form_id: int, vanilla_name: str,
                       tier_key, prefix: str, suffix: str):
        custom_rules_path = self._settings.value("paths/custom_rules", "")
        if not custom_rules_path:
            QMessageBox.warning(
                self, "No custom rules path",
                "Set a custom rules path in File → Settings… before saving."
            )
            return

        from tagger import build_rule, build_freeform_rule, upsert_custom_rule
        try:
            if tier_key:
                rule = build_rule(form_id, vanilla_name, tier_key, self._sort_tiers)
            else:
                rule = build_freeform_rule(form_id, vanilla_name, prefix, suffix)

            action = upsert_custom_rule(custom_rules_path, rule)
            self.statusBar().showMessage(
                f"Rule {action}: {vanilla_name}  →  {os.path.basename(custom_rules_path)}"
            )
        except Exception as exc:
            QMessageBox.critical(self, "Error saving rule", str(exc))

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def _open_settings(self, first_run: bool = False):
        # triggered signal passes a bool `checked` — normalise it
        if not isinstance(first_run, bool):
            first_run = False
        dlg = SettingsDialog(self, first_run=first_run)
        if dlg.exec():
            self._load_data()
