"""Check the usable message area and generation through the redesigned GUI."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PyQt6.QtGui import QFontDatabase
from PyQt6.QtCore import QPoint
from PyQt6.QtWidgets import QApplication

from src.canlibrarygenerator.__main__ import DBCLibraryGenerator


class WorkspaceLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        # Windows' offscreen plugin does not discover installed fonts.
        if os.name == "nt" and not QFontDatabase.families():
            for font in ("segoeui.ttf", "segoeuib.ttf"):
                QFontDatabase.addApplicationFont(str(Path(os.environ["WINDIR"]) / "Fonts" / font))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="can_gui_")
        self.addCleanup(self.temp.cleanup)
        self.dbc = Path(self.temp.name) / "workspace.dbc"
        self.dbc.write_text('\n'.join([
            'VERSION "test"', 'NS_ :', 'BS_:', 'BU_: FirstTx SecondTx Receiver',
            *[
                f'BO_ {256 + i} Msg{i}: 8 FirstTx\n'
                ' SG_ Value : 0|8@1+ (1,0) [0|255] "mps" Receiver'
                for i in range(32)
            ],
            'BO_TX_BU_ 256 : FirstTx,SecondTx;',
        ]), encoding="utf-8")
        self.window = DBCLibraryGenerator()
        self.window.show()
        self.addCleanup(self.window.close)
        with patch('src.canlibrarygenerator.__main__.QFileDialog.getOpenFileNames',
                   return_value=([str(self.dbc)], '')):
            self.window.open_files()
        self.settle()

    def settle(self):
        self.app.processEvents()
        self.app.processEvents()

    def test_small_windows_keep_many_messages_visible(self):
        for width, height in ((960, 540), (820, 500)):
            with self.subTest(size=(width, height)):
                self.window.resize(width, height)
                self.settle()
                tree = self.window.tree
                viewport = tree.viewport().rect()
                visible = sum(tree.visualItemRect(tree.topLevelItem(i)).intersects(viewport)
                              for i in range(tree.topLevelItemCount()))
                self.assertGreaterEqual(visible, 10)
                self.assertEqual((self.window.width(), self.window.height()), (width, height))
                self.assertGreater(tree.height(), height / 2)
                self.assertTrue(self.window.generate_button.isVisible())
                self.assertFalse(self.window.logo_label.pixmap().isNull())
                self.assertFalse(self.window.windowIcon().isNull())
                for size in (16, 32, 64):
                    self.assertFalse(self.window.windowIcon().pixmap(size, size).isNull())
                nodes = self.window.nodes_tree
                self.assertEqual(nodes.mapTo(self.window, QPoint()).y(),
                                 tree.mapTo(self.window, QPoint()).y())
                self.assertEqual(nodes.header().height(), tree.header().height())
                node_top = nodes.viewport().mapTo(self.window, QPoint()).y()
                message_top = tree.viewport().mapTo(self.window, QPoint()).y()
                self.assertEqual(node_top, message_top)

    def test_settings_hide_without_losing_options_or_panel_widths(self):
        self.window.chk_embedded.setChecked(True)
        self.window.chk_callback.setChecked(False)
        sizes = self.window.workspace_splitter.sizes()
        self.window.settings_button.click()
        self.settle()
        self.assertTrue(self.window.settings_panel.isHidden())
        self.assertGreater(self.window.messages_panel.width(), sizes[1])
        self.window.settings_button.click()
        self.settle()
        self.assertTrue(self.window.chk_embedded.isChecked())
        self.assertFalse(self.window.chk_callback.isChecked())
        self.assertEqual(self.window.workspace_splitter.sizes(), sizes)

    def test_invalid_prefix_does_not_create_output(self):
        self.window.nodes_tree._tx_cb['SecondTx'].setChecked(True)
        self.window.library_name_entry.setText('bad-prefix')
        with patch('src.canlibrarygenerator.__main__.QFileDialog.getExistingDirectory',
                   return_value=self.temp.name), \
             patch('src.canlibrarygenerator.__main__.QMessageBox.critical') as error:
            self.window.generate_library()
            error.assert_called_once()
        self.assertEqual([path.name for path in Path(self.temp.name).iterdir()], ['workspace.dbc'])

    def test_node_selection_summary_and_export_for_both_languages(self):
        self.window.nodes_tree._tx_cb['SecondTx'].setChecked(True)
        self.settle()
        self.assertEqual(self.window.selection_summary.text(), '1 selected · 0 RX · 1 TX')
        self.assertEqual(len(self.window.tree.get_checked()), 1)
        for language, header_ext, source_ext in ((0, 'h', 'c'), (1, 'hpp', 'cpp')):
            with self.subTest(language=language):
                self.window.language_group.button(language).setChecked(True)
                self.window.library_name_entry.setText(f'gui{language}')
                self.window.chk_embedded.setChecked(True)
                self.window.chk_unit.setChecked(True)
                self.window.chk_callback.setChecked(False)
                with patch('src.canlibrarygenerator.__main__.QFileDialog.getExistingDirectory',
                           return_value=self.temp.name), \
                     patch('src.canlibrarygenerator.__main__.QMessageBox.information') as success, \
                     patch('src.canlibrarygenerator.__main__.QMessageBox.critical') as error:
                    self.window.generate_button.click()
                    error.assert_not_called()
                    success.assert_called_once()
                output = Path(self.temp.name) / f'gui{language}'
                self.assertEqual(len(list(output.rglob('*.*'))), 5)
                header = (output / 'inc' / f'gui{language}_db.{header_ext}').read_text(encoding='utf-8')
                self.assertIn('Value_mps', header)
                definitions = (output / 'inc' / f'can_db_def.{header_ext}').read_text(encoding='utf-8')
                self.assertNotIn('can_db_callback_t', definitions)
                interface = (output / 'src' / f'gui{language}_interface.{source_ext}').read_text(encoding='utf-8')
                self.assertIn(f'gui{language}_Msg0_output_processing', interface)
        self.window.clear_selection_button.click()
        self.settle()
        self.assertEqual(self.window.selection_summary.text(), '0 selected · 0 RX · 0 TX')


if __name__ == '__main__':
    unittest.main()
