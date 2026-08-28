"""SearchBar — live item search widget.

Emits item_selected(form_id: int, name: str) when the user picks a result.
The parent must call set_data(vanilla_dict) once strings are loaded.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QLabel
)
from PySide6.QtCore import Signal, Qt


class SearchBar(QWidget):
    """
    A search field + auto-updating results list.

    Qt concepts used here:
      - QWidget subclassing (custom composite widget)
      - Signal/slot: item_selected is a custom Signal that the parent connects to
      - QListWidget for a scrollable item list; each item carries hidden data
        via item.setData(Qt.UserRole, value)
      - textChanged signal on QLineEdit drives the live filter
    """

    # Custom signal.  Syntax: Signal(type1, type2, ...)
    # Connected in main_window.py with:  self._search_bar.item_selected.connect(handler)
    item_selected = Signal(int, str)   # (form_id, name)

    MAX_RESULTS = 100   # cap results so the list never gets unwieldy
    MIN_CHARS   = 2     # don't search on single characters

    def __init__(self, parent=None):
        super().__init__(parent)
        self._vanilla: dict[int, str] = {}
        self._build_ui()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_data(self, vanilla: dict):
        """Load {form_id: name} from the backend after the data thread finishes."""
        self._vanilla = vanilla
        self._input.setEnabled(True)
        self._input.setPlaceholderText("Search item names…  (e.g. 'fasnacht')")

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Search field
        self._input = QLineEdit()
        self._input.setPlaceholderText("Loading…")
        self._input.setEnabled(False)
        self._input.setMinimumHeight(34)
        # textChanged fires on every keystroke — perfect for live filter
        self._input.textChanged.connect(self._on_text_changed)
        # Let the user navigate the list with keyboard after typing
        self._input.installEventFilter(self)

        # Small status line ("42 matches", "Showing 100 of 1234…", "No matches")
        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #888; font-size: 11px; padding-left: 2px;")
        self._status_label.hide()

        # Results list — shows below the input, hidden until there are results
        self._list = QListWidget()
        self._list.setMaximumHeight(220)
        self._list.hide()
        # itemClicked: mouse click; itemActivated: Enter key
        self._list.itemClicked.connect(self._select_item)
        self._list.itemActivated.connect(self._select_item)

        layout.addWidget(self._input)
        layout.addWidget(self._status_label)
        layout.addWidget(self._list)

    # ------------------------------------------------------------------
    # Slots (private)
    # ------------------------------------------------------------------

    def _on_text_changed(self, text: str):
        text = text.strip()
        if len(text) < self.MIN_CHARS:
            self._list.hide()
            self._status_label.hide()
            return

        q = text.lower()
        matches = sorted(
            [(fid, name) for fid, name in self._vanilla.items() if q in name.lower()],
            key=lambda x: x[1]
        )

        # Rebuild the list widget
        self._list.clear()
        for fid, name in matches[:self.MAX_RESULTS]:
            item = QListWidgetItem(name)
            # Qt.UserRole is a standard "user data" slot on every QListWidgetItem.
            # We stash the integer form_id here so we can retrieve it on click
            # without keeping a parallel data structure.
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
        """User picked a result — emit signal and collapse the list."""
        fid  = item.data(Qt.UserRole)
        name = item.text()
        self._input.setText(name)
        self._list.hide()
        self._status_label.hide()
        # Emit our custom signal — connected slots in parent receive (fid, name)
        self.item_selected.emit(fid, name)

    # ------------------------------------------------------------------
    # Keyboard: Down arrow from input moves focus to the list
    # ------------------------------------------------------------------

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        from PySide6.QtGui import QKeyEvent
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
