from dataclasses import dataclass, field
from typing import Dict, List, Set

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QCheckBox, QLabel, QTreeWidget, QTreeWidgetItem,
    QHeaderView, QGraphicsOpacityEffect,
)


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
        self._message_keys = {}
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

    def message_key(self, item_id):
        return self._message_keys.get(item_id)

    def set_message_key(self, item_id, key):
        self._message_keys[item_id] = key

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
        self._message_keys = {}


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
        # A message remains selected while either direction is enabled.
        selected = (self.tree.is_message_cell_checked(message_id, "RX") or
                    self.tree.is_message_cell_checked(message_id, "TX"))
        for sig_id in self.message_children.get(message_id, []):
            self._set_signal_checked(sig_id, selected)

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
