"""SearchBar — live item search widget.

Emits item_selected(form_id: int, name: str) when the user picks a result.
The parent must call set_data(focused, full) once strings are loaded.

Filter tiers (controlled by the "Include all strings" checkbox):
  Focused  (default) — mod-known items + Plan:/Recipe:/Formula: not yet in mod
                       ~7,300 items, zero dialogue/terminal noise
  Full               — heuristic-cleaned vanilla (no newlines, ≤80 chars)
                       ~146,000 items, for finding brand-new game additions
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QListWidget, QListWidgetItem, QLabel, QCheckBox
)
from PySide6.QtCore import Signal, Qt


class SearchBar(QWidget):
    """
    A search field + auto-updating results list with a two-tier data set.

    Qt concepts used here:
      - QWidget subclassing (custom composite widget)
      - Signal/slot: item_selected is a custom Signal the parent connects to
      - QListWidget with Qt.UserRole data: hidden form_id on each row
      - QCheckBox.toggled: switches the active dataset and re-runs the filter
      - textChanged on QLineEdit drives the live filter
      - eventFilter: intercepts Down-arrow / Escape from the text field
    """

    item_selected = Signal(int, str)   # (form_id, name)

    MAX_RESULTS = 100
    MIN_CHARS   = 2

    def __init__(self, parent=None):
        super().__init__(parent)
        # Two datasets, set by the parent after data loads
        self._focused: dict[int, str] = {}   # curated ~7,300 items
        self._full:    dict[int, str] = {}   # heuristic-cleaned ~146,000 items
        self._build_ui()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_data(self, focused: dict, full: dict):
        """
        Load both datasets once the background loader finishes.

        focused — mod-known items + prefixed new items (~7,300)
        full    — heuristic-cleaned vanilla strings (~146,000)
        """
        self._focused = focused
        self._full    = full
        self._input.setEnabled(True)
        self._input.setPlaceholderText("Search item names…  (e.g. 'fasnacht')")
        self._update_scope_label()
        # Re-run the filter in case the user already typed something
        self._on_text_changed(self._input.text())

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # ---- Top row: input + checkbox ----
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Loading…")
        self._input.setEnabled(False)
        self._input.setMinimumHeight(34)
        self._input.textChanged.connect(self._on_text_changed)
        self._input.installEventFilter(self)

        # Toggling this checkbox switches between the focused and full datasets.
        # QCheckBox.toggled(bool) fires whenever the check state changes.
        self._all_check = QCheckBox("Include all strings")
        self._all_check.setToolTip(
            "Off (default): search mod-known items + Plan:/Recipe: not yet in mod  (~7,300 items)\n"
            "On: search all heuristic-cleaned vanilla strings  (~146,000 items, includes noise)"
        )
        self._all_check.setEnabled(False)
        self._all_check.toggled.connect(self._on_scope_changed)

        top_row.addWidget(self._input, stretch=1)
        top_row.addWidget(self._all_check)
        layout.addLayout(top_row)

        # ---- Scope / status line ----
        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #888; font-size: 11px; padding-left: 2px;")
        self._status_label.hide()

        self._scope_label = QLabel("")
        self._scope_label.setStyleSheet("color: #555; font-size: 10px; padding-left: 2px;")
        layout.addWidget(self._scope_label)
        layout.addWidget(self._status_label)

        # ---- Results list ----
        self._list = QListWidget()
        self._list.setMaximumHeight(220)
        self._list.hide()
        self._list.itemClicked.connect(self._select_item)
        self._list.itemActivated.connect(self._select_item)
        layout.addWidget(self._list)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def _active_data(self) -> dict:
        return self._full if self._all_check.isChecked() else self._focused

    def _update_scope_label(self):
        if not self._focused:
            self._scope_label.setText("")
            return
        if self._all_check.isChecked():
            self._scope_label.setText(
                f"Searching all vanilla strings  ({len(self._full):,} items, may include noise)"
            )
        else:
            self._scope_label.setText(
                f"Searching mod-known items + new plans/recipes  ({len(self._focused):,} items)"
            )

    # ------------------------------------------------------------------
    # Slots (private)
    # ------------------------------------------------------------------

    def _on_scope_changed(self):
        """Checkbox toggled — update the scope label and re-run the search."""
        self._update_scope_label()
        self._on_text_changed(self._input.text())

    def _on_text_changed(self, text: str):
        text = text.strip()
        if len(text) < self.MIN_CHARS:
            self._list.hide()
            self._status_label.hide()
            return

        q = text.lower()
        matches = sorted(
            [(fid, name) for fid, name in self._active_data.items() if q in name.lower()],
            key=lambda x: x[1]
        )

        self._list.clear()
        for fid, name in matches[:self.MAX_RESULTS]:
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, fid)
            self._list.addItem(item)

        total = len(matches)
        if total > self.MAX_RESULTS:
            self._status_label.setText(
                f"Showing {self.MAX_RESULTS} of {total:,} matches — type more to narrow"
            )
        elif total == 1:
            self._status_label.setText("1 match")
        elif total > 1:
            self._status_label.setText(f"{total} matches")
        else:
            self._status_label.setText("No matches")

        self._status_label.show()
        self._list.setVisible(bool(matches))

    def _select_item(self, item: QListWidgetItem):
        fid  = item.data(Qt.UserRole)
        name = item.text()
        self._input.setText(name)
        self._list.hide()
        self._status_label.hide()
        self.item_selected.emit(fid, name)

    # ------------------------------------------------------------------
    # Keyboard: Down-arrow from input → list; Escape → hide list
    # ------------------------------------------------------------------

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if obj is self._input and event.type() == QEvent.KeyPress:
            key = event.key()
            if key == Qt.Key_Down and self._list.isVisible():
                self._list.setFocus()
                if self._list.currentRow() < 0 and self._list.count():
                    self._list.setCurrentRow(0)
                return True
            if key == Qt.Key_Escape:
                self._list.hide()
                self._status_label.hide()
                return True
        return super().eventFilter(obj, event)
