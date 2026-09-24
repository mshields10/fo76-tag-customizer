"""TagEditor — configuration panel shown once a search result is selected.

Qt concepts used here:
  - QFormLayout: two-column label/field layout
  - QRadioButton + toggled signal: mutually exclusive mode switching
  - QComboBox with userData: stores the tier key behind the display string
  - QFrame with HLine: visual separator
  - Live preview: slot connected to multiple widgets' change signals
  - Custom Signal with named parameters
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QComboBox, QLineEdit, QPushButton, QFrame, QRadioButton, QButtonGroup
)
from PySide6.QtCore import Signal, Qt


class TagEditor(QWidget):
    """
    Panel for configuring how a selected item should be tagged.

    Emits rule_ready(form_id, name, tier_key_or_None, prefix, suffix) when
    the user clicks Save — the parent (MainWindow) calls the backend from there.

    This widget deliberately does NOT import from the scripts/ backend.
    It only manages UI state and emits raw values upward.
    """

    # Signal carries everything the parent needs to call build_rule() or build_freeform_rule().
    # When tier_key is set (sort-tier mode):
    #   prefix  = source tag text (e.g. "BURN", "Infest") — empty means no tag
    #   suffix  = tag position ("suffix" or "before_plan")
    # When tier_key is None (freeform mode):
    #   prefix/suffix = literal text prepended/appended to the name
    rule_ready = Signal(int, str, object, str, str)
    # (form_id: int, vanilla_name: str, tier_key: str|None, prefix: str, suffix: str)

    def __init__(self, sort_tiers: dict, parent=None):
        super().__init__(parent)
        self._sort_tiers: dict = sort_tiers
        self._form_id: int | None = None
        self._vanilla_name: str | None = None
        self._build_ui()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_sort_tiers(self, sort_tiers: dict):
        """Called once data has loaded — populates the tier combo."""
        self._sort_tiers = sort_tiers
        self._tier_combo.clear()
        for key, info in sort_tiers.items():
            # addItem(display_text, userData=key) — Qt stores key behind the scenes
            self._tier_combo.addItem(info['description'], userData=key)
        self._update_preview()

    def set_item(self, form_id: int, vanilla_name: str):
        """Called by MainWindow when the user selects a search result."""
        self._form_id     = form_id
        self._vanilla_name = vanilla_name
        self._item_label.setText(f"{vanilla_name}  —  {form_id:#010x}")
        self._update_preview()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(10)

        # Visual separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep)

        # Selected item header
        self._item_label = QLabel("Select an item above to begin")
        self._item_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(self._item_label)

        # ---- Mode switcher ----
        mode_row = QHBoxLayout()
        self._sort_radio     = QRadioButton("Sort tier  (adds the rarity symbol + sort prefix)")
        self._freeform_radio = QRadioButton("Custom prefix / suffix")
        self._sort_radio.setChecked(True)
        # toggled fires when a radio button is turned on OR off;
        # connecting once to either button is enough because they're mutually exclusive.
        self._sort_radio.toggled.connect(self._on_mode_changed)
        mode_row.addWidget(self._sort_radio)
        mode_row.addWidget(self._freeform_radio)
        mode_row.addStretch()
        layout.addLayout(mode_row)

        # ---- Form fields ----
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)

        # Sort tier combo (Sort tier mode)
        self._tier_combo = QComboBox()
        self._tier_combo.setMinimumWidth(300)
        form.addRow("Sort tier:", self._tier_combo)

        # Source tag (Sort tier mode, optional) — for event/raid legendary mods
        self._tag_edit = QLineEdit()
        self._tag_edit.setPlaceholderText("Event/source label  e.g. BURN, Infest  (optional)")
        self._tag_label = QLabel("Source tag:")
        form.addRow(self._tag_label, self._tag_edit)

        # Tag position — only meaningful when source tag is filled
        pos_widget = QWidget()
        pos_row = QHBoxLayout(pos_widget)
        pos_row.setContentsMargins(0, 0, 0, 0)
        pos_row.setSpacing(16)
        self._pos_suffix_radio    = QRadioButton("After name  (e.g. ★★★ Glowing [BURN])")
        self._pos_prefix_radio    = QRadioButton("Before name  (e.g. ★★★ [BURN] Glowing — sorts by source)")
        self._pos_suffix_radio.setChecked(True)
        self._pos_group = QButtonGroup(self)
        self._pos_group.addButton(self._pos_suffix_radio)
        self._pos_group.addButton(self._pos_prefix_radio)
        pos_row.addWidget(self._pos_suffix_radio)
        pos_row.addWidget(self._pos_prefix_radio)
        pos_row.addStretch()
        self._pos_label = QLabel("Tag position:")
        form.addRow(self._pos_label, pos_widget)
        self._pos_widget = pos_widget

        # Prefix / suffix (Freeform mode) — initially hidden
        self._prefix_edit = QLineEdit()
        self._prefix_edit.setPlaceholderText("Text prepended before the item name  (optional)")
        self._suffix_edit = QLineEdit()
        self._suffix_edit.setPlaceholderText("Text appended after the item name  (optional)")
        self._prefix_label = QLabel("Prefix:")
        self._suffix_label = QLabel("Suffix:")
        form.addRow(self._prefix_label, self._prefix_edit)
        form.addRow(self._suffix_label, self._suffix_edit)

        layout.addLayout(form)

        # ---- Live preview ----
        preview_row = QHBoxLayout()
        preview_row.addWidget(QLabel("Preview:"))
        self._preview_label = QLabel("—")
        # Monospace + accent colour so the leading spaces are easy to read
        self._preview_label.setStyleSheet(
            "color: #4a9eff; font-family: 'Consolas', 'Courier New', monospace; "
            "background: #1a1a2e; padding: 4px 8px; border-radius: 4px;"
        )
        self._preview_label.setTextFormat(Qt.TextFormat.PlainText)
        preview_row.addWidget(self._preview_label)
        preview_row.addStretch()
        layout.addLayout(preview_row)

        # ---- Save button ----
        self._save_btn = QPushButton("Save Rule")
        self._save_btn.setFixedWidth(130)
        self._save_btn.setMinimumHeight(32)
        layout.addWidget(self._save_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        # Wire live preview signals
        self._tier_combo.currentIndexChanged.connect(self._update_preview)
        self._tag_edit.textChanged.connect(self._update_preview)
        self._pos_group.buttonToggled.connect(self._update_preview)
        self._prefix_edit.textChanged.connect(self._update_preview)
        self._suffix_edit.textChanged.connect(self._update_preview)

        # Save button
        self._save_btn.clicked.connect(self._on_save)

        # Initial visibility
        self._on_mode_changed()

    # ------------------------------------------------------------------
    # Slots (private)
    # ------------------------------------------------------------------

    def _on_mode_changed(self):
        """Show/hide fields depending on which radio button is active."""
        is_sort = self._sort_radio.isChecked()
        self._tier_combo.setVisible(is_sort)
        self._tag_label.setVisible(is_sort)
        self._tag_edit.setVisible(is_sort)
        self._pos_label.setVisible(is_sort)
        self._pos_widget.setVisible(is_sort)

        # FormLayout rows don't have a single show/hide handle, so toggle each widget
        self._prefix_label.setVisible(not is_sort)
        self._prefix_edit.setVisible(not is_sort)
        self._suffix_label.setVisible(not is_sort)
        self._suffix_edit.setVisible(not is_sort)

        self._update_preview()

    def _update_preview(self):
        """Recalculate and display the resulting item name."""
        if not self._vanilla_name:
            self._preview_label.setText("—")
            return

        if self._sort_radio.isChecked():
            key = self._tier_combo.currentData()
            if key and self._sort_tiers:
                info   = self._sort_tiers[key]
                symbol = info.get('symbol', '')
                spaces = info.get('lead_spaces', 0)
                tag    = self._tag_edit.text().strip()
                tag_str = f' [{tag}]' if tag else ''

                if tag and self._pos_prefix_radio.isChecked():
                    # Before name: ★★★ [BURN] Glowing
                    name_part = f'[{tag}] {self._vanilla_name}'
                else:
                    # After name (default): ★★★ Glowing [BURN]
                    name_part = f'{self._vanilla_name}{tag_str}'

                preview = f"{' ' * spaces}{symbol} {name_part}"
                self._preview_label.setText(preview)
            else:
                self._preview_label.setText("—")
        else:
            prefix  = self._prefix_edit.text()
            suffix  = self._suffix_edit.text()
            self._preview_label.setText(f"{prefix}{self._vanilla_name}{suffix}")

    def _on_save(self):
        """Validate and emit rule_ready to the parent."""
        if self._form_id is None or self._vanilla_name is None:
            return

        if self._sort_radio.isChecked():
            tier_key     = self._tier_combo.currentData()
            source_tag   = self._tag_edit.text().strip()
            tag_position = "before_plan" if self._pos_prefix_radio.isChecked() else "suffix"
            # In sort-tier mode the signal reuses prefix=source_tag, suffix=tag_position
            self.rule_ready.emit(self._form_id, self._vanilla_name, tier_key,
                                 source_tag, tag_position)
        else:
            prefix = self._prefix_edit.text()
            suffix = self._suffix_edit.text()
            self.rule_ready.emit(self._form_id, self._vanilla_name, None, prefix, suffix)
