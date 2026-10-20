"""Light and dark palettes shared by workspace controls."""
import darkdetect


def build_stylesheet(resource_path):
    if darkdetect.isDark():
        colors = dict(background="#2C2C2C", panel="#353535", text="#EEEEEE",
                      muted="#BBBBBB", border="#505050", input="#303030",
                      alternate="#343434", hover="#414141", selected="#254D68")
    else:
        colors = dict(background="#F0F0F0", panel="#F7F7F7", text="#222222",
                      muted="#555555", border="#C4C4C4", input="#FFFFFF",
                      alternate="#F7F7F7", hover="#E5E5E5", selected="#CCE8FF")
    colors["check_icon"] = resource_path("resources/icon/checkbox-checked.svg").replace("\\", "/")
    colors["radio_icon"] = resource_path("resources/icon/radio-checked.svg").replace("\\", "/")
    return """
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
    """ % colors
