import sys
import os
import darkdetect
import cantools
from PIL import Image, ImageQt

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QPushButton, QLabel, QLineEdit, QRadioButton, QButtonGroup,
    QTreeWidget, QTreeWidgetItem, QFileDialog, QMessageBox,
    QHeaderView, QCheckBox, QGraphicsOpacityEffect
)

from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional

from .generate_functions.generate_c_library import generate_c_code
from .generate_functions.generate_cpp_library import generate_cpp_code

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
class CheckableTreeWidget(QTreeWidget):

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
        # reagujeme jen na signály (child) a jen na levý checkbox (column 0)
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
    message_sender: Dict[str, Optional[str]] = field(default_factory=dict)
    message_receivers: Dict[str, Set[str]] = field(default_factory=dict)
    signal_receivers: Dict[str, Set[str]] = field(default_factory=dict)

    node_tx_messages: Dict[str, List[str]] = field(default_factory=dict)
    node_rx_signals: Dict[str, List[str]] = field(default_factory=dict)
    node_rx_messages: Dict[str, Set[str]] = field(default_factory=dict)

    signal_to_message: Dict[str, str] = field(default_factory=dict)

    # ---- Registration during loading ----
    def register_message(self, message_id: str, message_obj):
        self.message_children.setdefault(message_id, [])

        # Sender (first sender if list)
        sender = None
        try:
            if getattr(message_obj, 'senders', None):
                sender = message_obj.senders[0] if message_obj.senders else None
        except Exception:
            sender = None
        self.message_sender[message_id] = sender
        if sender:
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
        # TX side: sender node
        sender = self.message_sender.get(message_id)
        if sender:
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
        # (Optional) Symmetry for TX: enable only if sender exists
        # for msg_id, sender in self.message_sender.items():
        #     self.tree.set_message_cell_enabled(msg_id, 'TX', bool(sender))

    def on_signal_toggled(self, signal_id: str):
        return


class DBCLibraryGenerator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.controller = None
        self.nodes_tree = None
        self.setWindowTitle("CAN Library Generator")
        self.dbs = []  # List of loaded DBC databases
        self.tree = None  # CheckableTreeWidget for messages and signals
        self.files_label = None  # Label for selected files
        self.library_name_entry = None  # Entry for library name
        self.language_group = None  # QButtonGroup for language selection
        self.image = None  # To hold the PIL Image object

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
        """
        Applies a dark or light theme using QSS, mimicking sv_ttk.
        """
        checked_path = "src/canlibrarygenerator/png/checked.png"
        unchecked_path = "src/canlibrarygenerator/png/unchecked.png"

        # Převod na absolutní cestu
        checked_abs = os.path.abspath(checked_path)
        unchecked_abs = os.path.abspath(unchecked_path)

        # Pro Windows je potřeba převod lomítek
        checked_abs = checked_abs.replace('\\', '/')
        unchecked_abs = unchecked_abs.replace('\\', '/')
        # Common styles for both themes
        common_qss = """
        QGroupBox {
            border: 1px solid #444; /* Darker border for group boxes */
            border-radius: 6px;
            margin-top: 1ex; /* Space for the title */
            font-weight: bold;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left; /* Position at top left */
            padding: 0 5px; /* Padding around title text */
        }
        QPushButton {
            border-radius: 4px;
            padding: 6px 12px; /* Smaller padding for smaller buttons */
            font-weight: normal;
            border: 1px solid; /* Defined by theme */
        }
        QPushButton:hover {
            /* Handled by theme specific styles */
        }
        QPushButton:pressed {
            /* Handled by theme specific styles */
        }
        QPushButton#AccentButton {
            font-weight: bold;
            border: none; /* Accent button has no border in sv_ttk */
        }
        QLineEdit {
            border: 1px solid; /* Defined by theme */
            border-radius: 4px;
            padding: 4px;
        }
        QRadioButton {
            spacing: 5px; /* Space between radio button and text */
        }
        QTreeWidget {
            border: 1px solid; /* Defined by theme */
            border-radius: 4px;
            padding: 2px;
            show-decoration-selected: 1; /* Show checkmark when selected */
        }
        QHeaderView::section {
            padding: 6px; /* Padding for header text */
            border: none; /* No individual borders between sections */
            border-bottom: 2px solid #0078D7; /* Accent line at bottom */
            font-weight: bold;
            text-align: center; /* Center align header text */
        }
        QTreeWidget::item {
            padding: 3px 0; /* Padding for tree items */
        }
        QTreeWidget::item:hover {
            /* Handled by theme specific styles */
        }
        QTreeWidget::item:selected {
            /* Handled by theme specific styles */
        }
        QScrollBar:vertical {
            border: none; /* No border for scrollbar itself */
            background: transparent; /* Background of the scrollbar area */
            width: 12px;
            margin: 0px 0px 0px 0px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical {
            border-radius: 5px;
            min-height: 20px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            border: none;
            background: none;
        }
        QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
            width: 0px; /* Hide arrows */
            height: 0px;
        }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
            background: none;
        }

        """

        if darkdetect.isDark():
            theme_qss = """
            QMainWindow {
                background-color: #2C2C2C; /* sv_ttk dark background */
                color: #F0F0F0; /* sv_ttk text color */
            }
            QGroupBox {
                background-color: #3A3A3A; /* sv_ttk frame background */
                color: #F0F0F0;
                border-color: #4A4A4A; /* sv_ttk border color */
            }
            QGroupBox::title {
                color: #F0F0F0;
            }
            QPushButton {
                background-color: #4A4A4A; /* sv_ttk button background */
                border-color: #555555; /* sv_ttk button border */
                color: #F0F0F0;
            }
            QPushButton:hover {
                background-color: #555555; /* Slightly lighter on hover */
            }
            QPushButton:pressed {
                background-color: #3A3A3A; /* Slightly darker on press */
            }
            QPushButton#AccentButton {
                background-color: #0078D7; /* sv_ttk accent blue */
                color: white;
            }
            QPushButton#AccentButton:hover {
                background-color: #006AC1; /* Darker accent blue on hover */
            }
            QPushButton#AccentButton:pressed {
                background-color: #004C99; /* Even darker accent blue on press */
            }
            QLabel {
                color: #F0F0F0;
            }
            QLineEdit {
                background-color: #3A3A3A; /* sv_ttk entry background */
                border-color: #555555; /* sv_ttk entry border */
                color: #F0F0F0;
            }
            QRadioButton {
                color: #F0F0F0;
            }
            QTreeWidget {
                background-color: #3A3A3A; /* sv_ttk treeview background */
                color: #F0F0F0;
                border-color: #4A4A4A; /* sv_ttk treeview border */
                alternate-background-color: #444444; /* For alternating row colors */
            }
            QHeaderView::section {
                background-color: #3A3A3A; /* sv_ttk header background */
                color: #F0F0F0;
            }
            QTreeWidget::item:hover {
                background-color: rgba(0, 120, 215, 0.2); /* Light blue hover */
            }
            QTreeWidget::item:selected {
                background-color: rgba(0, 120, 215, 0.4); /* Darker blue selected */
            }
            QScrollBar::handle:vertical {
                background: #666666; /* Scrollbar handle color */
            }
            """
        else:  # Light theme
            theme_qss = """
            QMainWindow {
                background-color: #F0F0F0; /* sv_ttk light background */
            }
            QGroupBox {
                background-color: #FFFFFF; /* sv_ttk frame background */
                border-color: #CCCCCC; /* sv_ttk border color */
            }
            QPushButton {
                background-color: #EEEEEE; /* sv_ttk button background */
                border-color: #BBBBBB; /* sv_ttk button border */
            }
            QPushButton:hover {
                background-color: #DDDDDD; /* Slightly darker on hover */
            }
            QPushButton:pressed {
                background-color: #CCCCCC; /* Slightly darker on press */
            }
            QPushButton#AccentButton {
                background-color: #0078D7; /* sv_ttk accent blue */
                color: white;
            }
            QPushButton#AccentButton:hover {
                background-color: #006AC1; /* Darker accent blue on hover */
            }
            QPushButton#AccentButton:pressed {
                background-color: #004C99; /* Even darker accent blue on press */
            }
            QLabel {
                color: #333333;
            }
            QLineEdit {
                background-color: #FFFFFF; /* sv_ttk entry background */
                border-color: #BBBBBB; /* sv_ttk entry border */
                color: #333333;
            }
            QRadioButton {
                color: #333333;
            }
            QTreeWidget {
                color: #333333;
                border-color: #BBBBBB; /* sv_ttk treeview border */
                alternate-background-color: #F8F8F8; /* For alternating row colors */
            }
            QHeaderView::section {
                background-color: #EEEEEE; /* sv_ttk header background */
                color: #333333;
            }
            QTreeWidget::item:hover {
                background-color: rgba(0, 120, 215, 0.1); /* Light blue hover */
            }
            QTreeWidget::item:selected {
                background-color: rgba(0, 120, 215, 0.2); /* Darker blue selected */
            }
            QScrollBar::handle:vertical {
                background: #AAAAAA; /* Scrollbar handle color */
            }
            """
        self.setStyleSheet(common_qss + theme_qss)

    def setup_gui(self):
        """Initialize the GUI components."""
        self.setGeometry(100, 100, 920, 890)  # Set initial window size

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)  # Padding around the main content
        main_layout.setSpacing(10)  # Spacing between major sections

        # --- Top Frame: File Selection ---
        file_frame = QGroupBox("DBC File Selection")
        file_layout = QHBoxLayout(file_frame)
        file_layout.setContentsMargins(15, 20, 15, 10)  # Adjusted padding inside group box
        file_layout.setSpacing(10)  # Spacing between widgets in this layout

        # Button for open dialog
        select_files_button = QPushButton("📂 Select DBC Files")
        select_files_button.clicked.connect(self.open_files)
        file_layout.addWidget(select_files_button)

        # Label for selected files
        self.files_label = QLabel("No files selected.")
        self.files_label.setStyleSheet("color: gray;")  # Apply gray color directly
        file_layout.addWidget(self.files_label, 1)  # Stretch factor 1

        # VSB logo
        image_path = self.resource_path(os.path.join("png", "VSB-TUO_logo.png"))
        try:
            self.image = Image.open(image_path)
            self.image = self.image.resize((145, 62), Image.Resampling.LANCZOS)  # Use LANCZOS for quality

            # Convert PIL Image to QPixmap
            q_image = ImageQt.ImageQt(self.image)  # Use ImageQt for conversion
            logo_pixmap = QPixmap.fromImage(q_image)

            logo_label = QLabel()
            logo_label.setPixmap(logo_pixmap)
            logo_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
            file_layout.addWidget(logo_label)
        except Exception as e:
            print(f"Error loading image: {e}")
            logo_label = QLabel("Logo Missing")  # Placeholder if image fails
            logo_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
            file_layout.addWidget(logo_label)

        main_layout.addWidget(file_frame)

        # --- Middle Frame: NodeTreeView for nodes ---
        nodes_frame = QGroupBox("Nodes")
        nodes_layout = QVBoxLayout(nodes_frame)
        nodes_layout.setContentsMargins(15, 20, 15, 10)
        nodes_layout.setSpacing(5)

        self.nodes_tree = NodesTreeWidget()
        self.nodes_tree.header().setStretchLastSection(False)

        nodes_layout.addWidget(self.nodes_tree)
        main_layout.addWidget(nodes_frame)

        # --- Middle Frame: CheckboxTreeview for Messages and Signals ---
        tree_frame = QGroupBox("Messages and Signals")
        tree_layout = QVBoxLayout(tree_frame)
        tree_layout.setContentsMargins(15, 20, 15, 10)
        tree_layout.setSpacing(5)

        # CheckableTreeWidget for messages and signals
        self.tree = CheckableTreeWidget()
        self.tree.header().setStretchLastSection(False)  # Prevent last column from stretching automatically
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Make Name column stretchable
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        # Header text alignment is now handled by QSS (text-align: center)

        tree_layout.addWidget(self.tree)
        main_layout.addWidget(tree_frame, 1)  # Stretch factor 1 for tree frame

        self.controller = SelectionController(self.tree, self.nodes_tree)
        self.tree.set_controller(self.controller)
        self.nodes_tree.set_controller(self.controller)

        # --- Bottom Frame: Controls and Generation ---
        controls_frame = QGroupBox("Generation Settings")
        controls_layout = QGridLayout(controls_frame)
        controls_layout.setContentsMargins(15, 20, 15, 10)
        controls_layout.setSpacing(10)  # Spacing between widgets in this layout

        # Library name entry
        controls_layout.addWidget(QLabel("Library Name/Prefix:"), 0, 0, Qt.AlignmentFlag.AlignLeft)
        self.library_name_entry = QLineEdit("cangen")
        controls_layout.addWidget(self.library_name_entry, 0, 1, 1, 2)

        # Language selections
        controls_layout.addWidget(QLabel("Language:"), 0, 3,
                                  Qt.AlignmentFlag.AlignRight)  # Align right to push towards radios
        language_layout = QHBoxLayout()
        language_layout.setSpacing(5)
        self.language_group = QButtonGroup(self)  # Use a button group for radio buttons

        c_radio = QRadioButton("C")
        c_radio.setChecked(True)  # Default to C
        self.language_group.addButton(c_radio, 0)  # ID 0 for C
        language_layout.addWidget(c_radio)

        cpp_radio = QRadioButton("CPP")
        self.language_group.addButton(cpp_radio, 1)  # ID 1 for CPP
        language_layout.addWidget(cpp_radio)

        controls_layout.addLayout(language_layout, 0, 4, 1, 1)  # Only 1 column span now
        controls_layout.setColumnStretch(1, 1)

        # Selection buttons
        action_buttons_frame = QWidget()
        action_buttons_layout = QHBoxLayout(action_buttons_frame)
        action_buttons_layout.setContentsMargins(0, 0, 0, 0)  # No extra margins for this internal layout
        action_buttons_layout.setSpacing(10)  # Spacing between buttons
        action_buttons_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Center the buttons

        select_all_button = QPushButton("✅ Select All")
        select_all_button.clicked.connect(lambda: self.controller.select_all())
        action_buttons_layout.addWidget(select_all_button)

        deselect_all_button = QPushButton("❌ Deselect All")
        deselect_all_button.clicked.connect(lambda: self.controller.unselect_all())
        action_buttons_layout.addWidget(deselect_all_button)

        controls_layout.addWidget(action_buttons_frame, 1, 0, 1, 5)  # Span all 5 columns

        # Generate button
        generate_button = QPushButton("🚀 Generate Library")
        generate_button.setObjectName("AccentButton")  # Used for QSS styling
        generate_button.clicked.connect(self.generate_library)
        controls_layout.addWidget(generate_button, 2, 0, 1, 5,
                                  Qt.AlignmentFlag.AlignCenter)  # Span all 5 columns, center

        main_layout.addWidget(controls_frame)

        # --- Footer: App version ---
        version_label = QLabel(f"App version {__version__}")
        version_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        version_label.setStyleSheet("color: gray;")
        main_layout.addWidget(version_label)

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

        try:
            if language == "c":
                struct_h, struct_c, function_h, function_c = generate_c_code(selected_items_ids, library_name, self.dbs, self.tree, message_modes=message_modes)

                os.makedirs(os.path.join(directory, "includes"), exist_ok=True)
                os.makedirs(os.path.join(directory, "src"), exist_ok=True)

                h_file_path = os.path.join(directory, "includes", f"{library_name}_db.h")
                with open(h_file_path, "w") as h_file:
                    h_file.write(struct_h)

                c_file_path = os.path.join(directory, "src", f"{library_name}_db.c")
                with open(c_file_path, "w") as c_file:
                    c_file.write(struct_c)

                h_file_path = os.path.join(directory, "includes", f"{library_name}_interface.h")
                with open(h_file_path, "w") as h_file:
                    h_file.write(function_h)

                c_file_path = os.path.join(directory, "src", f"{library_name}_interface.c")
                with open(c_file_path, "w") as c_file:
                    c_file.write(function_c)

                QMessageBox.information(self, "Success",
                                        f"Generated {library_name}_db.c and {library_name}_interface.c \n "
                                        f"files in {directory}/src\n"
                                        f"Generated {library_name}_db.h and {library_name}_interface.c \n "
                                        f"files in {directory}/includes\n")
            else:  # language == "cpp"
                hpp_code, cpp_code = generate_cpp_code(selected_items_ids, library_name, self.dbs, self.tree)

                hpp_file_path = os.path.join(directory, f"{library_name}.hpp")
                with open(hpp_file_path, "w") as hpp_file:
                    hpp_file.write(hpp_code)

                cpp_file_path = os.path.join(directory, f"{library_name}.cpp")
                with open(cpp_file_path, "w") as cpp_file:
                    cpp_file.write(cpp_code)

                QMessageBox.information(self, "Success",
                                        f"Generated {library_name}.hpp and {library_name}.cpp \n "
                                        f"files in {directory}")

        except Exception as e:
            QMessageBox.critical(self, "Generation Error", f"An error occurred during {library_name} generation: {e}")


def main():
    app = QApplication(sys.argv)
    window = DBCLibraryGenerator()
    window.show()
    print("CAN_Library_Generator started...")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()