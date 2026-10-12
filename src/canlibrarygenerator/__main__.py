import sys
import os
import darkdetect
import cantools

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFrame, QSplitter, QScrollArea, QSizePolicy, QPushButton, QLabel, QLineEdit, QRadioButton, QButtonGroup,
    QTreeWidget, QTreeWidgetItem, QFileDialog, QMessageBox,
    QHeaderView, QCheckBox, QGraphicsOpacityEffect
)

from PyQt6.QtGui import QPixmap, QFont, QPainter, QIcon
from PyQt6.QtCore import Qt, QTimer, QSize, pyqtSignal

from dataclasses import dataclass, field
from typing import Dict, List, Set

from .generate_functions.generate_c_library import generate_c_code
from .generate_functions.generate_cpp_library import generate_cpp_code
from .ir.builder import _is_j1939_message, _is_can_fd_message

# Define your app version
__version__ = "dev"


def _apply_disabled_visual(cb: QCheckBox, enabled: bool):
    eff = cb.graphicsEffect()
    if not isinstance(eff, QGraphicsOpacityEffect):
        eff = QGraphicsOpacityEffect(cb)
        cb.setGraphicsEffect(eff)
    eff.setOpacity(1.0 if enabled else 0.35)
    cb.setCursor(Qt.CursorShape.ArrowCursor if enabled else Qt.CursorShape.ForbiddenCursor)

# -------------------------
# CheckableTreeWidget (Msgs)
# -------------------------
class ElidedLabel(QLabel):
    """Keep long DBC file lists from enlarging the window."""

    def setText(self, text):
        super().setText(text)
        self.setToolTip(text)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(self.palette().color(self.foregroundRole()))
        text = self.fontMetrics().elidedText(self.text(), Qt.TextElideMode.ElideRight, self.width())
        painter.drawText(self.contentsRect(), self.alignment(), text)


class CheckableTreeWidget(QTreeWidget):
    selection_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._block_signals = False
        self._suppress_cell_callbacks = False
        self._item_map: Dict[str, QTreeWidgetItem] = {}
        self._parent_id_map: Dict[str, str] = {}
        self._next_id = 0
        self._controller = None  # set via set_controller

        # keep pointers to message RX/TX QCheckBox widgets by message_id
        self._msg_rx_cb: Dict[str, QCheckBox] = {}
        self._msg_tx_cb: Dict[str, QCheckBox] = {}

        self.setHeaderLabels(["Name", "Type", "ID", "RX", "TX"])
        self.header().setStretchLastSection(False)
        self.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.header().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.header().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        self.itemChanged.connect(self._handle_item_changed)

    def set_controller(self, controller):
        self._controller = controller

    def _centered_checkbox(self, checked=False, tooltip=None, on_change=None) -> QWidget:
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cb = QCheckBox()
        cb.setChecked(checked)
        if tooltip:
            cb.setToolTip(tooltip)
        if on_change:
            cb.stateChanged.connect(on_change)
        cb.stateChanged.connect(lambda: self.selection_changed.emit())
        layout.addWidget(cb)
        w._checkbox = cb  # convenience pointer
        return w

    def _attach_rx_tx(self, item: QTreeWidgetItem, rx_checked=False, tx_checked=False):
        message_id = item.data(0, Qt.ItemDataRole.UserRole)
        rx_widget = self._centered_checkbox(
            checked=rx_checked,
            tooltip="Mark as RX for this message (selects all its signals)",
            on_change=lambda s, mid=message_id: (
                None if self._suppress_cell_callbacks else (
                    self._controller.on_message_toggle(mid, 'RX', bool(s)) if self._controller else None
                )
            ),
        )
        tx_widget = self._centered_checkbox(
            checked=tx_checked,
            tooltip="Mark as TX for this message (selects all its signals)",
            on_change=lambda s, mid=message_id: (
                None if self._suppress_cell_callbacks else (
                    self._controller.on_message_toggle(mid, 'TX', bool(s)) if self._controller else None
                )
            ),
        )
        self.setItemWidget(item, 3, rx_widget)
        self.setItemWidget(item, 4, tx_widget)
        # store actual checkbox pointers
        self._msg_rx_cb[message_id] = rx_widget._checkbox
        self._msg_tx_cb[message_id] = tx_widget._checkbox

    def set_message_cell_checked(self, message_id: str, which: str, checked: bool):
        cb = None
        if which == 'RX':
            cb = self._msg_rx_cb.get(message_id)
        else:
            cb = self._msg_tx_cb.get(message_id)
        if cb is not None:
            self._suppress_cell_callbacks = True
            cb.setChecked(bool(checked))
            self._suppress_cell_callbacks = False

    def is_message_cell_checked(self, message_id: str, which: str) -> bool:
        cb = self._msg_rx_cb.get(message_id) if which == 'RX' else self._msg_tx_cb.get(message_id)
        return bool(cb.isChecked()) if cb is not None else False

    def add_item(self, parent_q_item_or_id, text, values):
        parent_q_item = None
        parent_id = None

        if parent_q_item_or_id is None:
            new_item = QTreeWidgetItem(self, [text] + list(values) + ["", ""])  # pad RX/TX cols
        elif isinstance(parent_q_item_or_id, QTreeWidgetItem):
            parent_q_item = parent_q_item_or_id
            new_item = QTreeWidgetItem(parent_q_item, [text] + list(values) + ["", ""])  # pad RX/TX
            parent_id = parent_q_item.data(0, Qt.ItemDataRole.UserRole)
        elif isinstance(parent_q_item_or_id, str):
            parent_id = parent_q_item_or_id
            parent_q_item = self._item_map.get(parent_id)
            if not parent_q_item:
                raise ValueError(f"Parent item with ID '{parent_id}' not found.")
            new_item = QTreeWidgetItem(parent_q_item, [text] + list(values) + ["", ""])  # pad
        else:
            raise TypeError("parent_q_item_or_id must be None, QTreeWidgetItem, or item ID (str).")

        # Assign an ID and store maps
        item_id = f"qitem_{self._next_id}"
        self._next_id += 1
        self._item_map[item_id] = new_item
        new_item.setData(0, Qt.ItemDataRole.UserRole, item_id)

        # Messages (top-level): no left checkbox, attach RX/TX cell widgets
        is_message = (values and len(values) > 0 and str(values[0]) == "Message" and new_item.parent() is None)
        if is_message:
            new_item.setFlags(new_item.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
            self._attach_rx_tx(new_item)
        else:
            # Signals (children): keep left checkbox
            new_item.setFlags(new_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            new_item.setCheckState(0, Qt.CheckState.Unchecked)
            if parent_id:
                self._parent_id_map[item_id] = parent_id

        return item_id

    def _handle_item_changed(self, item: QTreeWidgetItem, column: int):
        if self._block_signals:
            return
        if item.parent() is None or column != 0:
            return
        if not (item.flags() & Qt.ItemFlag.ItemIsUserCheckable):
            return
        if self._controller:
            sig_id = item.data(0, Qt.ItemDataRole.UserRole)
            self._controller.on_signal_toggled(sig_id)

    def item(self, item_id, attribute=None):
        q_item = self._item_map.get(item_id)
        if q_item:
            item_data = {
                'text': q_item.text(0),
                'values': [q_item.text(1), q_item.text(2)],  # Type, ID
            }
            if attribute:
                return item_data.get(attribute)
            return item_data
        return None

    def parent(self, item_id):
        return self._parent_id_map.get(item_id)

    def get_checked(self):
        """Return IDs of checked SIGNAL items only (parents are not checkable)."""
        checked_ids = []
        for item_id, q_item in self._item_map.items():
            if q_item.parent() is not None and \
               (q_item.flags() & Qt.ItemFlag.ItemIsUserCheckable) and \
               q_item.checkState(0) in (Qt.CheckState.Checked, Qt.CheckState.PartiallyChecked):
                checked_ids.append(item_id)
        return checked_ids

    def set_message_cell_enabled(self, message_id: str, which: str, enabled: bool):
        cb = self._msg_rx_cb.get(message_id) if which == 'RX' else self._msg_tx_cb.get(message_id)
        if cb is not None:
            cb.setEnabled(bool(enabled))
            _apply_disabled_visual(cb, bool(enabled))

    def clear(self):
        super().clear()
        self._item_map.clear()
        self._parent_id_map.clear()
        self._msg_rx_cb.clear()
        self._msg_tx_cb.clear()
        self._next_id = 0


# =============================
# Nodes Tree
# =============================
class NodesTreeWidget(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._controller = None
        self._rx_cb: Dict[str, QCheckBox] = {}
        self._tx_cb: Dict[str, QCheckBox] = {}
        self._suppress_cell_callbacks = False

        self.setHeaderLabels(["Node", "RX", "TX"])
        self.header().setStretchLastSection(False)
        self.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

    def set_controller(self, controller):
        self._controller = controller

    def _centered_checkbox(self, checked=False, tooltip=None, on_change=None) -> QWidget:
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cb = QCheckBox()
        cb.setChecked(checked)
        if tooltip:
            cb.setToolTip(tooltip)
        if on_change:
            cb.stateChanged.connect(on_change)
        layout.addWidget(cb)
        w._checkbox = cb
        return w

    def _norm_node(self, name) -> str:
        return (str(name) if name is not None else "").strip()

    def add_node(self, node_name: str, rx=False, tx=False):
        item = QTreeWidgetItem([node_name, "", ""])  # placeholders for RX/TX widgets
        item.setToolTip(0, node_name)
        self.addTopLevelItem(item)

        rxw = self._centered_checkbox(
            rx,
            tooltip=f"{node_name}: RX",
            on_change=lambda s, n=node_name: (
                None if self._suppress_cell_callbacks else (
                    self._controller.on_node_toggle(n, 'RX', bool(s)) if self._controller else None
                )
            ),
        )
        txw = self._centered_checkbox(
            tx,
            tooltip=f"{node_name}: TX",
            on_change=lambda s, n=node_name: (
                None if self._suppress_cell_callbacks else (
                    self._controller.on_node_toggle(n, 'TX', bool(s)) if self._controller else None
                )
            ),
        )
        self.setItemWidget(item, 1, rxw)
        self.setItemWidget(item, 2, txw)
        self._rx_cb[node_name] = rxw._checkbox
        self._tx_cb[node_name] = txw._checkbox
        return item

    def set_node_cell_checked(self, node_name: str, which: str, checked: bool):
        cb = self._rx_cb.get(node_name) if which == 'RX' else self._tx_cb.get(node_name)
        if cb is not None:
            self._suppress_cell_callbacks = True
            cb.setChecked(bool(checked))
            self._suppress_cell_callbacks = False

    def is_node_cell_checked(self, node_name: str, which: str) -> bool:
        cb = self._rx_cb.get(node_name) if which == 'RX' else self._tx_cb.get(node_name)
        return bool(cb.isChecked()) if cb is not None else False

    def set_node_cell_enabled(self, node_name: str, which: str, enabled: bool):
        cb = self._rx_cb.get(node_name) if which == 'RX' else self._tx_cb.get(node_name)
        if cb is not None:
            cb.setEnabled(bool(enabled))
            _apply_disabled_visual(cb, bool(enabled))

    def clear(self):
        super().clear()
        self._rx_cb.clear()
        self._tx_cb.clear()


# =============================
# Selection Controller
# =============================
@dataclass
class SelectionController:
    tree: CheckableTreeWidget
    nodes_tree: NodesTreeWidget

    # Indexes keyed by stable item_id strings
    message_children: Dict[str, List[str]] = field(default_factory=dict)
    message_senders: Dict[str, Set[str]] = field(default_factory=dict)
    message_receivers: Dict[str, Set[str]] = field(default_factory=dict)
    signal_receivers: Dict[str, Set[str]] = field(default_factory=dict)

    node_tx_messages: Dict[str, List[str]] = field(default_factory=dict)
    node_rx_signals: Dict[str, List[str]] = field(default_factory=dict)
    node_rx_messages: Dict[str, Set[str]] = field(default_factory=dict)

    signal_to_message: Dict[str, str] = field(default_factory=dict)

    # ---- Registration during loading ----
    def register_message(self, message_id: str, message_obj):
        self.message_children.setdefault(message_id, [])

        # Register every transmitter, including additional BO_TX_BU_ nodes.
        senders = {sender for sender in (message_obj.senders or []) if sender}
        self.message_senders[message_id] = senders
        for sender in senders:
            self.node_tx_messages.setdefault(sender, []).append(message_id)

        # Receivers at message level (fallback when signals lack receivers)
        recs: Set[str] = set()
        try:
            if getattr(message_obj, 'receivers', None):
                for r in message_obj.receivers:
                    if r:
                        recs.add(r)
        except Exception:
            pass
        self.message_receivers[message_id] = recs
        for r in recs:
            self.node_rx_messages.setdefault(r, set()).add(message_id)

    def register_signal(self, message_id: str, signal_id: str, signal_obj):
        # Link signal under message
        self.message_children.setdefault(message_id, []).append(signal_id)

        self.signal_to_message[signal_id] = message_id

        # Receivers at signal level (preferred)
        recs: Set[str] = set()
        try:
            if getattr(signal_obj, 'receivers', None):
                for r in signal_obj.receivers:
                    if r:
                        recs.add(r)
        except Exception:
            pass
        if not recs:
            recs = set(self.message_receivers.get(message_id, set()))
        self.signal_receivers[signal_id] = recs

        for r in recs:
            self.node_rx_signals.setdefault(r, []).append(signal_id)
            self.node_rx_messages.setdefault(r, set()).add(message_id)

    # ---- GUI callbacks ----
    def on_message_toggle(self, message_id: str, which: str, checked: bool):
        # which is 'RX' or 'TX' → same effect: (de)select all child signals
        for sig_id in self.message_children.get(message_id, []):
            self._set_signal_checked(sig_id, checked)

        # After toggling a message, update the corresponding node cell(s)
        # TX side: synchronize all transmitter nodes.
        for sender in self.message_senders.get(message_id, set()):
            self._update_node_tx_state(sender)
        # RX side: all receiver nodes for this message
        for node in self._receivers_for_message(message_id):
            self._update_node_rx_state(node)

    def on_node_toggle(self, node_name: str, which: str, checked: bool):
        if which == 'TX':
            # Toggle all messages that this node transmits
            for msg_id in self.node_tx_messages.get(node_name, []):
                # Toggling the message cell will also toggle its signals via on_message_toggle
                self.tree.set_message_cell_checked(msg_id, 'TX', checked)
                self.on_message_toggle(msg_id, 'TX', checked)
            # Ensure node TX cell reflects the aggregate
            self.nodes_tree.set_node_cell_checked(node_name, 'TX', self._all_node_tx_messages_checked(node_name))
        else:  # 'RX'
            # Toggle all messages where this node is a receiver
            for msg_id in self.node_rx_messages.get(node_name, set()):
                self.tree.set_message_cell_checked(msg_id, 'RX', checked)
                self.on_message_toggle(msg_id, 'RX', checked)
            # Ensure node RX cell reflects the aggregate
            self.nodes_tree.set_node_cell_checked(node_name, 'RX', self._all_node_rx_messages_checked(node_name))

    # ---- Helpers ----
    def _set_signal_checked(self, signal_id: str, checked: bool):
        item = self.tree._item_map.get(signal_id)
        if item is not None:
            item.setCheckState(0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)

    def _receivers_for_message(self, message_id: str) -> Set[str]:
        nodes: Set[str] = set()
        for sig_id in self.message_children.get(message_id, []):
            nodes.update(self.signal_receivers.get(sig_id, set()))
        if not nodes:
            nodes.update(self.message_receivers.get(message_id, set()))
        return nodes

    def _all_node_tx_messages_checked(self, node_name: str) -> bool:
        msgs = self.node_tx_messages.get(node_name, [])
        if not msgs:
            return False
        return all(self.tree.is_message_cell_checked(mid, 'TX') for mid in msgs)

    def _all_node_rx_messages_checked(self, node_name: str) -> bool:
        msgs = list(self.node_rx_messages.get(node_name, set()))
        if not msgs:
            return False
        return all(self.tree.is_message_cell_checked(mid, 'RX') for mid in msgs)

    def _update_node_tx_state(self, node_name: str):
        self.nodes_tree.set_node_cell_checked(node_name, 'TX', self._all_node_tx_messages_checked(node_name))

    def _update_node_rx_state(self, node_name: str):
        self.nodes_tree.set_node_cell_checked(node_name, 'RX', self._all_node_rx_messages_checked(node_name))

    def select_all(self):
        """Select all nodes/messages/signals, but only in directions that exist for each node."""
        # 1) All TX-capable nodes → check TX
        for node in list(self.node_tx_messages.keys()):
            # This cascades to mark all its messages and signals TX-checked
            self.on_node_toggle(node, 'TX', True)
        # 2) All RX-capable nodes → check RX
        for node in list(self.node_rx_messages.keys()):
            self.on_node_toggle(node, 'RX', True)

    def unselect_all(self):
        """Clear all nodes/messages/signals for both RX and TX (only where applicable)."""
        # 1) All TX-capable nodes → uncheck TX
        for node in list(self.node_tx_messages.keys()):
            self.on_node_toggle(node, 'TX', False)
        # 2) All RX-capable nodes → uncheck RX
        for node in list(self.node_rx_messages.keys()):
            self.on_node_toggle(node, 'RX', False)

    def apply_enable_states(self):
        """Enable/disable node/message RX/TX checkboxes according to DBC topology."""
        # Nodes: enable if there is at least one message in that direction
        # We iterate over all nodes present in the GUI (from nodes_tree maps)
        for node in list(self.nodes_tree._tx_cb.keys()):
            has_tx = node in self.node_tx_messages and len(self.node_tx_messages[node]) > 0
            self.nodes_tree.set_node_cell_enabled(node, 'TX', has_tx)
        for node in list(self.nodes_tree._rx_cb.keys()):
            has_rx = node in self.node_rx_messages and len(self.node_rx_messages[node]) > 0
            self.nodes_tree.set_node_cell_enabled(node, 'RX', has_rx)
        # Messages: enable RX only if there is at least one receiver (signal or message level)
        for msg_id in self.message_children.keys():
            has_rx = len(self._receivers_for_message(msg_id)) > 0
            self.tree.set_message_cell_enabled(msg_id, 'RX', has_rx)

    def on_signal_toggled(self, signal_id: str):
        return


class DBCLibraryGenerator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.controller = None
        self.nodes_tree = None
        self.setWindowTitle("CAN Library Generator")
        icon = QIcon(self.resource_path("resources/icon/icon.png"))
        for size in (16, 24, 32, 48, 64, 128, 256):
            icon.addFile(self.resource_path(f"resources/icon/icon-{size}.png"), QSize(size, size))
        self.setWindowIcon(icon)
        self.dbs = []  # List of loaded DBC databases
        self.tree = None  # CheckableTreeWidget for messages and signals
        self.files_label = None  # Label for selected files
        self.library_name_entry = None  # Entry for library name
        self.language_group = None  # QButtonGroup for language selection
        self.chk_gen_def = None
        self.chk_embedded = None
        self.chk_unit = None
        self.chk_counter = None
        self.chk_crc = None
        self.chk_callback = None

        self.setup_gui()
        self.apply_theme()

    def resource_path(self, relative_path):
        """
        Get the absolute path to a resource, handling PyInstaller bundling.
        """
        if hasattr(sys, '_MEIPASS'):
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        else:
            # Running in a normal Python environment
            base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, relative_path)

    def apply_theme(self):
        """Apply the same restrained palette to all workspace panels."""
        if darkdetect.isDark():
            colors = dict(background="#2C2C2C", panel="#353535", text="#EEEEEE",
                          muted="#BBBBBB", border="#505050", input="#303030",
                          alternate="#343434", hover="#414141", selected="#254D68")
        else:
            colors = dict(background="#F0F0F0", panel="#F7F7F7", text="#222222",
                          muted="#555555", border="#C4C4C4", input="#FFFFFF",
                          alternate="#F7F7F7", hover="#E5E5E5", selected="#CCE8FF")
        colors["check_icon"] = self.resource_path("resources/icon/checkbox-checked.svg").replace("\\", "/")
        colors["radio_icon"] = self.resource_path("resources/icon/radio-checked.svg").replace("\\", "/")
        self.setStyleSheet("""
            QMainWindow, QWidget#Workspace { background: %(background)s; }
            QWidget { color: %(text)s; }
            QFrame#Panel { background: %(panel)s; border: 1px solid %(border)s; border-radius: 10px; }
            QLabel { background: transparent; }
            QLabel#PanelTitle { font-weight: 600; }
            QLabel#SecondaryLabel { color: %(muted)s; }
            QPushButton {
                background: %(panel)s; border: 1px solid %(border)s;
                border-radius: 7px; padding: 6px 10px;
            }
            QPushButton:hover { background: %(hover)s; }
            QPushButton:pressed, QPushButton:checked { background: %(selected)s; }
            QPushButton#AccentButton { background: #0078D7; color: white; border-color: #0078D7; }
            QPushButton#AccentButton:hover { background: #006AC1; }
            QPushButton#AccentButton:pressed { background: #004C99; }
            QLineEdit {
                background: %(input)s; border: 1px solid %(border)s;
                border-radius: 6px; padding: 5px 7px;
            }
            QLineEdit:focus { border-color: #0078D7; }
            QCheckBox, QRadioButton { background: transparent; spacing: 7px; }
            QCheckBox::indicator, QTreeWidget::indicator {
                width: 14px; height: 14px; border: 1px solid %(border)s;
                border-radius: 4px; background: %(input)s;
            }
            QCheckBox::indicator:checked, QTreeWidget::indicator:checked {
                background: #0078D7; border-color: #0078D7; image: url("%(check_icon)s");
            }
            QCheckBox::indicator:hover, QTreeWidget::indicator:hover { border-color: #0078D7; }
            QRadioButton::indicator {
                width: 14px; height: 14px; border: 1px solid %(border)s;
                border-radius: 8px; background: %(input)s;
            }
            QRadioButton::indicator:checked {
                background: #0078D7; border-color: #0078D7; image: url("%(radio_icon)s");
            }
            QTreeWidget {
                background: %(input)s; alternate-background-color: %(alternate)s;
                border: 1px solid %(border)s; border-radius: 7px; padding: 2px;
                selection-background-color: %(selected)s; selection-color: %(text)s;
            }
            QTreeWidget::item { padding: 4px 0; }
            QTreeWidget::item:hover { background: %(hover)s; }
            QTreeWidget::item:selected { background: %(selected)s; color: %(text)s; }
            QHeaderView::section {
                background: %(panel)s; color: %(text)s; padding: 6px 4px;
                border: none; border-bottom: 1px solid %(border)s;
            }
            QSplitter::handle { background: %(background)s; }
            QSplitter::handle:hover { background: %(border)s; border-radius: 3px; }
            QScrollArea#SettingsScroll, QWidget#SettingsContents { background: transparent; border: none; }
            QScrollBar:vertical { background: transparent; width: 10px; margin: 0; }
            QScrollBar::handle:vertical { background: %(border)s; border-radius: 5px; min-height: 24px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
        """ % colors)
        self._align_table_headers()

    def _align_table_headers(self):
        # Match the node title row to the message toolbar after styling.
        title_height = max(self.nodes_title.sizeHint().height(),
                           self.select_all_button.sizeHint().height(),
                           self.clear_selection_button.sizeHint().height())
        self.nodes_title.setFixedHeight(title_height)
        self.select_all_button.setFixedHeight(title_height)
        self.clear_selection_button.setFixedHeight(title_height)
        header_height = max(self.nodes_tree.header().sizeHint().height(),
                            self.tree.header().sizeHint().height())
        self.nodes_tree.header().setFixedHeight(header_height)
        self.tree.header().setFixedHeight(header_height)

    @staticmethod
    def _panel(title=None):
        panel = QFrame()
        panel.setObjectName("Panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        if title:
            label = QLabel(title)
            label.setObjectName("PanelTitle")
            layout.addWidget(label)
        return panel, layout

    def setup_gui(self):
        """Keep the message tree tall, with resizable side panels."""
        self.setMinimumSize(820, 420)
        available = self.screen().availableGeometry()
        self.resize(min(1200, max(820, available.width() - 48)),
                    min(760, max(420, available.height() - 64)))
        self.setFont(QFont("Segoe UI", 10))
        central = QWidget()
        central.setObjectName("Workspace")
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        file_panel, _ = self._panel()
        # The file toolbar remains compact regardless of window height.
        file_layout = file_panel.layout()
        file_layout.setContentsMargins(12, 8, 12, 8)
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)
        select_files = QPushButton("Select DBC Files")
        select_files.clicked.connect(self.open_files)
        toolbar.addWidget(select_files)
        self.files_label = ElidedLabel("No files selected.")
        self.files_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        file_details = QWidget()
        file_details.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        details_layout = QVBoxLayout(file_details)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(3)
        details_layout.addWidget(self.files_label)
        self.file_metadata = ElidedLabel()
        self.file_metadata.setObjectName("SecondaryLabel")
        self.file_metadata.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.file_metadata.hide()
        details_layout.addWidget(self.file_metadata)
        toolbar.addWidget(file_details, 1)
        self.settings_button = QPushButton("Settings")
        self.settings_button.setCheckable(True)
        self.settings_button.setChecked(True)
        self.settings_button.setToolTip("Show or hide generation settings")
        self.settings_button.toggled.connect(self._toggle_settings)
        toolbar.addWidget(self.settings_button)
        self.logo_label = QLabel()
        logo = QPixmap(self.resource_path(os.path.join("png", "VSB-TUO_logo.png")))
        if not logo.isNull():
            self.logo_label.setPixmap(logo.scaled(145, 62, Qt.AspectRatioMode.KeepAspectRatio,
                                                Qt.TransformationMode.SmoothTransformation))
        self.logo_label.setFixedSize(145, 62)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        toolbar.addWidget(self.logo_label)
        file_layout.addLayout(toolbar)
        layout.addWidget(file_panel)

        self.workspace_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.workspace_splitter.setChildrenCollapsible(False)
        self.workspace_splitter.setHandleWidth(8)
        self.nodes_panel, nodes_layout = self._panel("Nodes")
        self.nodes_title = nodes_layout.itemAt(0).widget()
        self.nodes_panel.setMinimumWidth(160)
        self.nodes_tree = NodesTreeWidget()
        self.nodes_tree.setRootIsDecorated(False)
        self.nodes_tree.setUniformRowHeights(True)
        for column in (1, 2):
            self.nodes_tree.header().setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
            self.nodes_tree.setColumnWidth(column, 36)
        nodes_layout.addWidget(self.nodes_tree, 1)
        self.workspace_splitter.addWidget(self.nodes_panel)

        self.messages_panel, messages_layout = self._panel()
        self.messages_panel.setMinimumWidth(340)
        message_toolbar = QHBoxLayout()
        title = QLabel("Messages & Signals")
        title.setObjectName("PanelTitle")
        message_toolbar.addWidget(title, 1)
        self.select_all_button = QPushButton("Select All")
        self.select_all_button.clicked.connect(lambda: self.controller.select_all())
        self.clear_selection_button = QPushButton("Clear")
        self.clear_selection_button.clicked.connect(lambda: self.controller.unselect_all())
        message_toolbar.addWidget(self.select_all_button)
        message_toolbar.addWidget(self.clear_selection_button)
        messages_layout.addLayout(message_toolbar)
        self.tree = CheckableTreeWidget()
        self.tree.setUniformRowHeights(True)
        self.tree.setAlternatingRowColors(True)
        # Keep the internal Type column for the controller, but omit it visually.
        self.tree.setColumnHidden(1, True)
        self.tree.headerItem().setText(2, "CAN ID")
        for column, width in ((2, 112), (3, 36), (4, 36)):
            self.tree.header().setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
            self.tree.setColumnWidth(column, width)
        messages_layout.addWidget(self.tree, 1)
        self.workspace_splitter.addWidget(self.messages_panel)

        self.controller = SelectionController(self.tree, self.nodes_tree)
        self.tree.set_controller(self.controller)
        self.nodes_tree.set_controller(self.controller)
        self.settings_panel, settings_layout = self._panel("Generation Settings")
        self.settings_panel.setMinimumWidth(250)
        self.settings_panel.setMaximumWidth(360)
        scroll = QScrollArea()
        scroll.setObjectName("SettingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        contents = QWidget()
        contents.setObjectName("SettingsContents")
        options_layout = QVBoxLayout(contents)
        options_layout.setContentsMargins(0, 0, 0, 0)
        options_layout.setSpacing(12)
        options_layout.addWidget(QLabel("Library Name/Prefix:"))
        self.library_name_entry = QLineEdit("cangen")
        options_layout.addWidget(self.library_name_entry)
        options_layout.addWidget(QLabel("Language:"))
        language_layout = QHBoxLayout()
        self.language_group = QButtonGroup(self)
        for identifier, name in enumerate(("C", "C++")):
            radio = QRadioButton(name)
            self.language_group.addButton(radio, identifier)
            radio.setChecked(identifier == 0)
            language_layout.addWidget(radio)
        language_layout.addStretch()
        options_layout.addLayout(language_layout)
        options_layout.addSpacing(8)
        option_definitions = [
            ("chk_gen_def", "Generate can_db_def header", True,
             "Uncheck if you already have a can_db_def header file."),
            ("chk_embedded", "Embedded library", False,
             "Generate an optimized library with lower memory use."),
            ("chk_unit", "Signal names with units", False,
             "Append units to signal names, for example sigVehicle_speed_mps."),
            ("chk_counter", "Message counter processing", True,
             "Generate automatic TX message counter processing."),
            ("chk_crc", "CRC processing", True,
             "Generate automatic CRC calculation in TX output processing."),
            ("chk_callback", "Message callbacks", True,
             "Generate message callback support for initialization, RX and TX processing."),
        ]
        for attribute, text, checked, tooltip in option_definitions:
            checkbox = QCheckBox(text)
            checkbox.setChecked(checked)
            checkbox.setToolTip(tooltip)
            setattr(self, attribute, checkbox)
            options_layout.addWidget(checkbox)
        options_layout.addStretch(1)
        scroll.setWidget(contents)
        settings_layout.addWidget(scroll, 1)
        self.workspace_splitter.addWidget(self.settings_panel)
        self.workspace_splitter.setStretchFactor(0, 0)
        self.workspace_splitter.setStretchFactor(1, 1)
        self.workspace_splitter.setStretchFactor(2, 0)
        self.workspace_splitter.setSizes([200, 680, 280])
        layout.addWidget(self.workspace_splitter, 1)

        footer = QHBoxLayout()
        self.selection_summary = QLabel("0 selected · 0 RX · 0 TX")
        self.selection_summary.setObjectName("SecondaryLabel")
        footer.addWidget(self.selection_summary)
        footer.addStretch(1)
        version_label = QLabel(f"Version {__version__}")
        version_label.setObjectName("SecondaryLabel")
        footer.addWidget(version_label)
        self.generate_button = QPushButton("Generate Library")
        self.generate_button.setObjectName("AccentButton")
        self.generate_button.clicked.connect(self.generate_library)
        footer.addWidget(self.generate_button)
        layout.addLayout(footer)

        # Coalesce cascaded node/signal toggles into one summary refresh.
        self.summary_timer = QTimer(self)
        self.summary_timer.setSingleShot(True)
        self.summary_timer.timeout.connect(self._update_selection_summary)
        self.tree.selection_changed.connect(self._schedule_selection_summary)
        self.tree.itemChanged.connect(self._schedule_selection_summary)
        self._settings_sizes = [200, 680, 280]

    def _toggle_settings(self, visible):
        if not visible:
            self._settings_sizes = self.workspace_splitter.sizes()
        self.settings_panel.setVisible(visible)
        if visible:
            sizes = self._settings_sizes.copy()
            available = self.workspace_splitter.width() - 2 * self.workspace_splitter.handleWidth()
            sizes[1] = max(self.messages_panel.minimumWidth(), available - sizes[0] - sizes[2])
            self.workspace_splitter.setSizes(sizes)

    def _schedule_selection_summary(self, *_):
        self.summary_timer.start(0)

    def _update_selection_summary(self):
        selected_messages = {self.tree.parent(item) for item in self.tree.get_checked()}
        rx = sum(self.tree.is_message_cell_checked(item, "RX") for item in selected_messages)
        tx = sum(self.tree.is_message_cell_checked(item, "TX") for item in selected_messages)
        self.selection_summary.setText(f"{len(selected_messages)} selected · {rx} RX · {tx} TX")

    def _update_file_metadata(self):
        descriptions = []
        for db in self.dbs:
            types = set()
            for message in db.messages:
                is_fd = _is_can_fd_message(message, db)
                if _is_j1939_message(message, db):
                    types.add("J1939 (CAN FD)" if is_fd else "J1939")
                else:
                    types.add("CAN FD" if is_fd else "CAN")
            bus_type = " / ".join(sorted(types)) or "Type not specified"
            version = str(db.version).strip() if db.version is not None else ""
            version_label = f"Version {version}" if version else "Version not specified"
            description = f"{bus_type} · {version_label}"
            if len(self.dbs) > 1:
                description = f"{db.name}: {description}"
            descriptions.append(description)
        self.file_metadata.setText("  |  ".join(descriptions))
        self.file_metadata.setToolTip("\n".join(descriptions))
        self.file_metadata.setVisible(bool(descriptions))

    def _fit_nodes_panel(self):
        """Choose an initial width that accommodates the loaded node names."""
        tree = self.nodes_tree
        name_width = max(tree.sizeHintForColumn(0), tree.header().sectionSizeHint(0))
        margins = self.nodes_panel.layout().contentsMargins()
        desired = (name_width + tree.columnWidth(1) + tree.columnWidth(2)
                   + 2 * tree.frameWidth() + tree.verticalScrollBar().sizeHint().width()
                   + margins.left() + margins.right())
        sizes = self.workspace_splitter.sizes()
        settings_visible = not self.settings_panel.isHidden()
        handles = 2 if settings_visible else 1
        available = self.workspace_splitter.width() - handles * self.workspace_splitter.handleWidth()
        settings_width = sizes[2] if settings_visible else 0
        maximum = available - self.messages_panel.minimumWidth() - settings_width
        nodes_width = max(self.nodes_panel.minimumWidth(), min(desired, maximum))
        self.workspace_splitter.setSizes([
            nodes_width, max(self.messages_panel.minimumWidth(), available - nodes_width - settings_width),
            settings_width,
        ])
        if not settings_visible:
            self._settings_sizes[0] = nodes_width

    def open_files(self):
        """Open multiple DBC files and load their content into the widgets."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select DBC files",
            "",
            "DBC files (*.dbc)"
        )
        if file_paths:
            shortened_file_paths = [os.path.basename(file_path) for file_path in file_paths]
            self.files_label.setText(f"Selected files: {', '.join(shortened_file_paths)}")
            self.dbs.clear()
            self.tree.clear()
            # reinit controller so indices are clean
            self.controller = SelectionController(self.tree, self.nodes_tree)
            self.tree.set_controller(self.controller)
            self.nodes_tree.set_controller(self.controller)
            if hasattr(self, 'nodes_tree'):
                self.nodes_tree.clear()

            node_names = set()

            for file_path in file_paths:
                try:
                    db = cantools.database.load_file(file_path)
                    db.name = os.path.basename(file_path)
                    self.dbs.append(db)

                    # --- Collect nodes for the top widget ---
                    if hasattr(db, 'nodes') and db.nodes:
                        for n in db.nodes:
                            name = getattr(n, 'name', str(n))
                            if name:
                                node_names.add(name)
                    else:
                        # Fallback: derive from message senders/receivers
                        for message in db.messages:
                            for s in getattr(message, 'senders', []) or []:
                                if s:
                                    node_names.add(s)
                            rec = getattr(message, 'receivers', []) or []
                            for r in (rec if isinstance(rec, (list, tuple, set)) else [rec]):
                                if r:
                                    node_names.add(r)

                    # --- Populate Messages & Signals (your existing behavior) ---
                    for message in db.messages:
                        message_id = self.tree.add_item(None, message.name, ("Message", hex(message.frame_id)))
                        self.controller.register_message(message_id, message)
                        for signal in message.signals:
                            signal_id = self.tree.add_item(message_id, signal.name, ("Signal", ""))
                            self.controller.register_signal(message_id, signal_id, signal)

                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Can't read DBC file {file_path}: {e}")

            # --- Render collected nodes ---
            if hasattr(self, 'nodes_tree'):
                for name in sorted(node_names):
                    self.nodes_tree.add_node(name)

            self.controller.apply_enable_states()
            self._fit_nodes_panel()
            self._update_file_metadata()
            self._schedule_selection_summary()

    def build_message_mode_map(self) -> dict:
        """Returns { message_id: {"rx": bool, "tx": bool} } for every message."""
        modes = {}
        for message_id in self.controller.message_children.keys():
            modes[message_id] = {
                "rx": bool(self.tree.is_message_cell_checked(message_id, "RX")),
                "tx": bool(self.tree.is_message_cell_checked(message_id, "TX")),
            }
        return modes

    def generate_library(self):
        """Generate C/C++ library from selected messages and signals."""
        selected_items_ids = self.tree.get_checked()
        message_modes = self.build_message_mode_map()
        if not selected_items_ids:
            QMessageBox.warning(self, "Warning", "No items selected for generation.")
            return

        if not self.dbs:
            QMessageBox.warning(self, "Warning", "No DBC files loaded.")
            return

        library_name = self.library_name_entry.text().strip()
        if not library_name:
            library_name = "cangen"

        directory = QFileDialog.getExistingDirectory(
            self,
            "Select directory to save the library"
        )
        if not directory:
            return

        language_id = self.language_group.checkedId()
        language = "c" if language_id == 0 else "cpp"

        embedded = self.chk_embedded.isChecked()
        with_units = self.chk_unit.isChecked()
        generate_counter = self.chk_counter.isChecked()
        generate_crc = self.chk_crc.isChecked()
        generate_callback = self.chk_callback.isChecked()

        try:
            lib_dir = os.path.join(directory, library_name)
            inc_dir = os.path.join(lib_dir, "inc")
            src_dir = os.path.join(lib_dir, "src")

            os.makedirs(inc_dir, exist_ok=True)
            os.makedirs(src_dir, exist_ok=True)

            if language == "c":
                ext_h, ext_c = ".h", ".c"
                contents = generate_c_code(
                    selected_items_ids, library_name, self.dbs, self.tree, __version__, message_modes=message_modes, embedded=embedded, with_units=with_units,
                    generate_counter=generate_counter, generate_crc=generate_crc, generate_callback=generate_callback
                )
            else:
                ext_h, ext_c = ".hpp", ".cpp"
                contents = generate_cpp_code(
                    selected_items_ids, library_name, self.dbs, self.tree, __version__, message_modes=message_modes, embedded=embedded, with_units=with_units,
                    generate_counter=generate_counter, generate_crc=generate_crc, generate_callback=generate_callback
                )

            def_h, db_h, db_c, int_h, int_c = contents

            files_to_write = {
                os.path.join(inc_dir, f"{library_name}_db{ext_h}"): db_h,
                os.path.join(src_dir, f"{library_name}_db{ext_c}"): db_c,
                os.path.join(inc_dir, f"{library_name}_interface{ext_h}"): int_h,
                os.path.join(src_dir, f"{library_name}_interface{ext_c}"): int_c
            }

            if self.chk_gen_def.isChecked():
                files_to_write[os.path.join(inc_dir, f"can_db_def{ext_h}")] = def_h

            for filepath, content in files_to_write.items():
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)

            QMessageBox.information(self, "Success",
                                    f"Generated {library_name}_db{ext_c} and {library_name}_interface{ext_c}\n"
                                    f"files in {library_name}/src\n"
                                    f"Generated {library_name}_db{ext_h}, {library_name}_interface{ext_h} and can_db_def{ext_h}\n"
                                    f"files in {library_name}/inc\n")

        except Exception as e:
            QMessageBox.critical(self, "Generation Error", f"An error occurred during {library_name} generation: {e}")


def main():
    print(f"cantools version: {cantools.__version__}")
    app = QApplication(sys.argv)
    window = DBCLibraryGenerator()
    app.setWindowIcon(window.windowIcon())
    window.show()
    print("CAN_Library_Generator started...")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
