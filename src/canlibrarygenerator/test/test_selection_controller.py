"""Regression tests for messages with more than one transmitter."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import unittest

import cantools
from PyQt6.QtWidgets import QApplication
from src.canlibrarygenerator.__main__ import (
    CheckableTreeWidget, NodesTreeWidget, SelectionController,
)


class MultipleTransmitterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tree = CheckableTreeWidget()
        self.nodes = NodesTreeWidget()
        self.controller = SelectionController(self.tree, self.nodes)
        self.tree.set_controller(self.controller)
        self.nodes.set_controller(self.controller)
        dbc = '\n'.join([
            'VERSION "test"', 'NS_ :', 'BS_:',
            'BU_: aaaaDummyNode DBW2TI Receiver',
            *[
                f'BO_ {i} EPSI{i}_DBWT_68_13: 8 aaaaDummyNode\n'
                ' SG_ Value : 0|8@1+ (1,0) [0|255] "" Receiver'
                for i in range(1, 4)
            ],
            *[f'BO_TX_BU_ {i} : aaaaDummyNode,DBW2TI;' for i in range(1, 4)],
        ])
        db = cantools.database.load_string(dbc, database_format="dbc")
        self.message_ids = []
        for msg in db.messages:
            mid = self.tree.add_item(None, msg.name, ("Message", hex(msg.frame_id)))
            self.message_ids.append(mid)
            self.controller.register_message(mid, msg)
            for sig in msg.signals:
                sid = self.tree.add_item(mid, sig.name, ("Signal", ""))
                self.controller.register_signal(mid, sid, sig)
        for node in db.nodes:
            self.nodes.add_node(node.name)
        self.controller.apply_enable_states()

    def tearDown(self):
        self.tree.close()
        self.nodes.close()
        self.tree.deleteLater()
        self.nodes.deleteLater()
        self.app.processEvents()

    def assert_messages_selected(self, selected):
        for mid in self.message_ids:
            self.assertEqual(self.tree.is_message_cell_checked(mid, "TX"), selected)
        self.assertEqual(len(self.tree.get_checked()), 3 if selected else 0)

    def test_second_transmitter_selects_messages_and_signals(self):
        self.nodes._tx_cb["DBW2TI"].setChecked(True)
        self.assert_messages_selected(True)
        self.assertTrue(self.nodes.is_node_cell_checked("aaaaDummyNode", "TX"))
        self.nodes._tx_cb["DBW2TI"].setChecked(False)
        self.assert_messages_selected(False)
        self.assertFalse(self.nodes.is_node_cell_checked("aaaaDummyNode", "TX"))

    def test_first_transmitter_and_manual_message_toggle_sync_all_nodes(self):
        self.nodes._tx_cb["aaaaDummyNode"].setChecked(True)
        self.assert_messages_selected(True)
        self.assertTrue(self.nodes.is_node_cell_checked("DBW2TI", "TX"))
        self.tree._msg_tx_cb[self.message_ids[0]].setChecked(False)
        for node in ["aaaaDummyNode", "DBW2TI"]:
            self.assertFalse(self.nodes.is_node_cell_checked(node, "TX"))
        self.tree._msg_tx_cb[self.message_ids[0]].setChecked(True)
        for node in ["aaaaDummyNode", "DBW2TI"]:
            self.assertTrue(self.nodes.is_node_cell_checked(node, "TX"))

    def test_select_all_and_unselect_all(self):
        self.controller.select_all()
        self.assert_messages_selected(True)
        self.controller.unselect_all()
        self.assert_messages_selected(False)

    def test_rx_off_preserves_signals_while_tx_remains_enabled(self):
        mid = self.message_ids[0]
        self.tree._msg_tx_cb[mid].setChecked(True)
        self.tree._msg_rx_cb[mid].setChecked(True)
        self.tree._msg_rx_cb[mid].setChecked(False)
        self.assertTrue(self.tree.is_message_cell_checked(mid, 'TX'))
        self.assertEqual(len(self.tree.get_checked()), 1)
        self.tree._msg_tx_cb[mid].setChecked(False)
        self.assertEqual(self.tree.get_checked(), [])


if __name__ == "__main__":
    unittest.main()
