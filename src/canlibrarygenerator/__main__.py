"""Desktop application entry point."""
import sys

import cantools
import darkdetect
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox

from . import __version__
from .ui.window import DBCLibraryGenerator
from .ui.selection import CheckableTreeWidget, NodesTreeWidget, SelectionController


def main():
    print(f"cantools version: {cantools.__version__}")
    app = QApplication(sys.argv)
    window = DBCLibraryGenerator()
    app.setWindowIcon(window.windowIcon())
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
