import os
import sys

from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QFont, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFrame, QSplitter,
    QScrollArea, QSizePolicy, QPushButton, QLabel, QLineEdit, QRadioButton,
    QButtonGroup, QFileDialog, QMessageBox, QHeaderView, QCheckBox,
)

from .. import __version__
from ..generate_functions.generate_c_library import generate_c_code
from ..generate_functions.generate_cpp_library import generate_cpp_code
from ..ir.builder import _is_j1939_message, _is_can_fd_message
from ..service import load_database, export_library
from .selection import CheckableTreeWidget, NodesTreeWidget, SelectionController, ElidedLabel
from .theme import build_stylesheet


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
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, relative_path)

    def apply_theme(self):
        self.setStyleSheet(build_stylesheet(self.resource_path))
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

            for db_index, file_path in enumerate(file_paths):
                try:
                    db = load_database(file_path)
                    db.name = os.path.basename(file_path)
                    db_index = len(self.dbs)
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
                        self.tree.set_message_key(message_id, (db_index, message.frame_id, message.is_extended_frame))
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
            if language == "c":
                contents = generate_c_code(
                    selected_items_ids, library_name, self.dbs, self.tree, __version__, message_modes=message_modes, embedded=embedded, with_units=with_units,
                    generate_counter=generate_counter, generate_crc=generate_crc, generate_callback=generate_callback
                )
            else:
                contents = generate_cpp_code(
                    selected_items_ids, library_name, self.dbs, self.tree, __version__, message_modes=message_modes, embedded=embedded, with_units=with_units,
                    generate_counter=generate_counter, generate_crc=generate_crc, generate_callback=generate_callback
                )

            written = export_library(contents, library_name, directory, language,
                                     include_definitions=self.chk_gen_def.isChecked())
            QMessageBox.information(self, "Success",
                                    f"Generated {len(written)} files in {os.path.join(directory, library_name)}")

        except Exception as e:
            QMessageBox.critical(self, "Generation Error", f"An error occurred during {library_name} generation: {e}")
