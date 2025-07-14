import sys
import os
import darkdetect
import cantools
from PIL import Image, ImageQt

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QPushButton, QLabel, QLineEdit, QRadioButton, QButtonGroup,
    QTreeWidget, QTreeWidgetItem, QFileDialog, QMessageBox,
    QHeaderView  # For controlling header behavior
)
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt, QSize

from .generate_functions.generate_c_library import generate_c_code
from .generate_functions.generate_cpp_library import generate_cpp_code

# Define your app version
__version__ = "dev"


class CheckableTreeWidget(QTreeWidget):
    """
    A custom QTreeWidget that supports checkboxes for items,
    mimicking Tkinter's CheckboxTreeview behavior more closely.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.itemChanged.connect(self._handle_item_changed)
        self.setSelectionMode(QTreeWidget.SelectionMode.NoSelection)  # Disable selection by default
        self._block_signals = False  # To prevent recursive calls during state changes
        self._item_map = {}  # Map unique ID (str) to QTreeWidgetItem
        self._parent_id_map = {}  # Map child_id (str) to parent_id (str)
        self._next_id = 0

    def _handle_item_changed(self, item, column):
        """
        Handles state changes for checkboxes.
        If a parent is checked/unchecked, all children follow.
        If a child is checked/unchecked, its parent's state is updated.
        """
        if self._block_signals:
            return

        self._block_signals = True  # Block signals to prevent recursion

        current_state = item.checkState(column)

        # If item is a parent (has children)
        if item.childCount() > 0:
            for i in range(item.childCount()):
                child = item.child(i)
                # Only change if different to avoid unnecessary signal emission
                if child.checkState(column) != current_state:
                    child.setCheckState(column, current_state)

        # If item is a child, update parent's state
        parent = item.parent()
        if parent:
            self._update_parent_check_state(parent, column)

        self._block_signals = False  # Unblock signals

    def _update_parent_check_state(self, parent_item, column):
        """
        Updates the parent's check state based on its children's states.
        If all children are checked, parent is checked.
        If all children are unchecked, parent is unchecked.
        If some children are checked and some are not, parent is partially checked (tristate).
        """
        checked_children = 0
        unchecked_children = 0
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            if child.checkState(column) == Qt.CheckState.Checked:
                checked_children += 1
            elif child.checkState(column) == Qt.CheckState.Unchecked:
                unchecked_children += 1

        if checked_children == parent_item.childCount():
            new_state = Qt.CheckState.Checked
        elif unchecked_children == parent_item.childCount():
            new_state = Qt.CheckState.Unchecked
        else:
            # Tristate: some checked, some unchecked
            new_state = Qt.CheckState.PartiallyChecked

        if parent_item.checkState(column) != new_state:
            parent_item.setCheckState(column, new_state)

    def add_item(self, parent_q_item_or_id, text, values):
        """
        Helper to add items to the tree and assign unique IDs,
        mimicking Tkinter's insert and returning an ID.
        parent_q_item_or_id can be a QTreeWidgetItem object or its ID (string).
        """
        parent_q_item = None
        parent_id = None

        if parent_q_item_or_id is None:
            new_item = QTreeWidgetItem(self, [text] + list(values))
        elif isinstance(parent_q_item_or_id, QTreeWidgetItem):
            parent_q_item = parent_q_item_or_id
            new_item = QTreeWidgetItem(parent_q_item, [text] + list(values))
            parent_id = parent_q_item.data(0, Qt.ItemDataRole.UserRole)  # Get parent's ID
        elif isinstance(parent_q_item_or_id, str):  # If an ID is passed
            parent_id = parent_q_item_or_id
            parent_q_item = self._item_map.get(parent_id)
            if parent_q_item:
                new_item = QTreeWidgetItem(parent_q_item, [text] + list(values))
            else:
                raise ValueError(f"Parent item with ID '{parent_id}' not found.")
        else:
            raise TypeError("parent_q_item_or_id must be None, QTreeWidgetItem, or item ID (str).")

        new_item.setFlags(new_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        new_item.setCheckState(0, Qt.CheckState.Unchecked)

        # Assign a unique ID and store in map
        item_id = f"qitem_{self._next_id}"  # Simple string ID
        self._next_id += 1
        self._item_map[item_id] = new_item

        # Store the ID in the item itself for easy retrieval later
        # This is primarily for internal consistency check, get_checked() will use _item_map directly
        new_item.setData(0, Qt.ItemDataRole.UserRole, item_id)

        # Store parent relationship
        if parent_id:
            self._parent_id_map[item_id] = parent_id

        # print(f"DEBUG: Added item '{text}' with ID '{item_id}'. Parent ID: {parent_id}") # Keep for detailed debug if needed
        return item_id  # Return the ID, similar to Tkinter's insert

    def item(self, item_id, attribute=None):
        """
        Mimics Tkinter's tree.item(item_id, attribute=None) behavior.
        Returns a dictionary for all attributes if attribute is None,
        or a specific attribute value if specified.
        """
        q_item = self._item_map.get(item_id)
        if q_item:
            item_data = {
                'text': q_item.text(0),
                'values': [q_item.text(1), q_item.text(2)],  # Column 1 (Type), Column 2 (ID)
                # Add other properties if generate_functions need them, e.g., 'tags'
                # For example, if they expect 'tags', you might need to store them in UserRole data
            }
            if attribute:
                return item_data.get(attribute)
            return item_data
        # print(f"DEBUG: item('{item_id}') returned None (not found in _item_map).") # Keep for detailed debug if needed
        return None  # Returns None if item_id is not found in _item_map

    def parent(self, item_id):
        """
        Mimics Tkinter's tree.parent(item_id) behavior by returning the parent's ID.
        """
        return self._parent_id_map.get(item_id)

    def get_checked(self):
        """
        Returns a list of unique IDs of checked items.
        This method now directly uses the internal _item_map for robustness.
        """
        checked_ids = []
        # Iterate through all items stored in the internal map
        print("DEBUG: Entering get_checked()")
        for item_id, q_item in self._item_map.items():
            current_check_state = q_item.checkState(0)
            print(f"DEBUG: Item ID: {item_id}, Text: {q_item.text(0)}, CheckState: {current_check_state}")
            if current_check_state == Qt.CheckState.Checked or \
                    current_check_state == Qt.CheckState.PartiallyChecked:
                # The item_id is already the correct unique ID (the key in the map)
                checked_ids.append(item_id)
        print(f"DEBUG: get_checked() returning: {checked_ids}")
        return checked_ids

    def change_state(self, item_id, state):
        """
        Changes the check state of an item by its ID.
        """
        q_item = self._item_map.get(item_id)
        if q_item:
            check_state = Qt.CheckState.Checked if state == "checked" else Qt.CheckState.Unchecked
            q_item.setCheckState(0, check_state)
        else:
            print(f"Warning: Item with ID '{item_id}' not found for state change.")

    def clear(self):
        """Clears the treeview and resets internal maps."""
        super().clear()
        self._item_map.clear()
        self._parent_id_map.clear()
        self._next_id = 0


class DBCLibraryGenerator(QMainWindow):
    def __init__(self):
        super().__init__()
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
                color: #333333; /* sv_ttk text color */
            }
            QGroupBox {
                background-color: #FFFFFF; /* sv_ttk frame background */
                color: #333333;
                border-color: #CCCCCC; /* sv_ttk border color */
            }
            QGroupBox::title {
                color: #333333;
            }
            QPushButton {
                background-color: #EEEEEE; /* sv_ttk button background */
                border-color: #BBBBBB; /* sv_ttk button border */
                color: #333333;
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
                background-color: #FFFFFF; /* sv_ttk treeview background */
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
        self.setGeometry(100, 100, 700, 600)  # Set initial window size

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

        # --- Middle Frame: CheckboxTreeview for Messages and Signals ---
        tree_frame = QGroupBox("Messages and Signals")
        tree_layout = QVBoxLayout(tree_frame)
        tree_layout.setContentsMargins(15, 20, 15, 10)
        tree_layout.setSpacing(5)

        # CheckableTreeWidget for messages and signals
        self.tree = CheckableTreeWidget()
        self.tree.setHeaderLabels(["Name", "Type", "ID"])
        # Set column widths and stretch
        self.tree.setColumnWidth(0, 280)  # Fixed width for Name
        self.tree.setColumnWidth(1, 100)  # Fixed width for Type
        self.tree.setColumnWidth(2, 100)  # Fixed width for ID
        self.tree.header().setStretchLastSection(False)  # Prevent last column from stretching automatically
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Make Name column stretchable
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        # Header text alignment is now handled by QSS (text-align: center)

        tree_layout.addWidget(self.tree)
        main_layout.addWidget(tree_frame, 1)  # Stretch factor 1 for tree frame

        # --- Bottom Frame: Controls and Generation ---
        controls_frame = QGroupBox("Generation Settings")
        controls_layout = QGridLayout(controls_frame)
        controls_layout.setContentsMargins(15, 20, 15, 10)
        controls_layout.setSpacing(10)  # Spacing between widgets in this layout

        # Library name entry
        controls_layout.addWidget(QLabel("Library Name:"), 0, 0, Qt.AlignmentFlag.AlignLeft)
        self.library_name_entry = QLineEdit("dbc_library")
        controls_layout.addWidget(self.library_name_entry, 0, 1, 1, 2)  # Span 2 columns

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
        select_all_button.clicked.connect(self.select_all)
        action_buttons_layout.addWidget(select_all_button)

        deselect_all_button = QPushButton("❌ Deselect All")
        deselect_all_button.clicked.connect(self.deselect_all)
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
        """Open multiple DBC files and load their content into the CheckableTreeWidget."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select DBC files",
            "",  # Default directory
            "DBC files (*.dbc)"
        )
        if file_paths:
            shortened_file_paths = [os.path.basename(file_path) for file_path in file_paths]
            self.files_label.setText(f"Selected files: {', '.join(shortened_file_paths)}")
            self.dbs.clear()  # Clear previously loaded databases
            self.tree.clear()  # Clear the CheckableTreeWidget and its internal maps

            for file_path in file_paths:
                try:
                    db = cantools.database.load_file(file_path)
                    self.dbs.append(db)

                    for message in db.messages:
                        # Use add_item to create the message item and get its ID
                        message_id = self.tree.add_item(None, message.name, ("Message", hex(message.frame_id)))
                        # We don't need to get the QTreeWidgetItem object here, add_item handles it
                        # The message_id is enough for tree.parent() and tree.item() later

                        for signal in message.signals:
                            # Use add_item to create the signal item as a child, passing parent ID
                            self.tree.add_item(message_id, signal.name, ("Signal", ""))

                    # self.tree.expandAll() # Removed as per user request to keep collapsed

                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Can't read DBC file {file_path}: {e}")

    def select_all(self):
        """Select all items in the CheckableTreeWidget."""
        self.tree._block_signals = True  # Block signals during bulk update
        print("DEBUG: Selecting all items...")
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            item.setCheckState(0, Qt.CheckState.Checked)  # Select message
            for j in range(item.childCount()):
                child = item.child(j)
                child.setCheckState(0, Qt.CheckState.Checked)  # Select signal
        self.tree._block_signals = False  # Unblock signals
        # Manually trigger parent state update after bulk change if needed,
        # though _handle_item_changed should cover it for individual changes.
        # For select_all, all parents will naturally become checked.

    def deselect_all(self):
        """Deselect all items in the CheckableTreeWidget."""
        self.tree._block_signals = True  # Block signals during bulk update
        print("DEBUG: Deselecting all items...")
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            item.setCheckState(0, Qt.CheckState.Unchecked)  # Deselect message
            for j in range(item.childCount()):
                child = item.child(j)
                child.setCheckState(0, Qt.CheckState.Unchecked)  # Deselect signal
        self.tree._block_signals = False  # Unblock signals
        # For deselect_all, all parents will naturally become unchecked.

    def generate_library(self):
        """Generate C/C++ library from selected messages and signals."""
        selected_items_names = self.tree.get_checked()  # Get all checked items by name
        if not selected_items_names:
            QMessageBox.warning(self, "Warning", "No items selected for generation.")
            return

        if not self.dbs:
            QMessageBox.warning(self, "Warning", "No DBC files loaded.")
            return

        library_name = self.library_name_entry.text().strip()
        if not library_name:
            library_name = "dbc_library"

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
                h_code, c_code = generate_c_code(selected_items_names, library_name, self.dbs, self.tree)

                h_file_path = os.path.join(directory, f"{library_name}.h")
                with open(h_file_path, "w") as h_file:
                    h_file.write(h_code)

                c_file_path = os.path.join(directory, f"{library_name}.c")
                with open(c_file_path, "w") as c_file:
                    c_file.write(c_code)

                QMessageBox.information(self, "Success",
                                        f"Generated {library_name}.h and {library_name}.c \n "
                                        f"files in {directory}")
            else:  # language == "cpp"
                hpp_code, cpp_code = generate_cpp_code(selected_items_names, library_name, self.dbs, self.tree)

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
    # Import ImageQt after QApplication is created, as it depends on QtGui
    # This import is necessary for PIL to convert to QPixmap
    from PIL import ImageQt
    window = DBCLibraryGenerator()
    window.show()
    print("CAN_Library_Generator started...")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()