import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from ttkwidgets import CheckboxTreeview
import cantools
from collections import defaultdict
import os


class DBCLibraryGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("Library generator for DBC files")
        self.dbs = []  # List of loaded DBC databases
        self.tree = None  # CheckboxTreeview for messages and signals
        self.label = None  # Label for selected files
        self.library_name_entry = None  # Entry for library name
        self.setup_gui()

    def setup_gui(self):
        """Initialize the GUI components."""
        # Button for open dialog
        button = ttk.Button(self.root, text="Select DBC files", command=self.open_files)
        button.pack(pady=10)

        # Label for selected files
        self.label = ttk.Label(self.root, text="No files selected.")
        self.label.pack(pady=10)

        # CheckboxTreeview for messages and signals
        self.tree = CheckboxTreeview(self.root, columns=("Type", "ID"), show="tree headings")
        self.tree.heading("#0", text="Name")
        self.tree.heading("Type", text="Type")
        self.tree.heading("ID", text="ID")
        self.tree.pack(pady=10, fill=tk.BOTH, expand=True)

        # Frame for library name, language selection and generate button
        bottom_frame = ttk.Frame(self.root)
        bottom_frame.pack(pady=10, fill=tk.X)

        # Entry for library name
        ttk.Label(bottom_frame, text="Library Name:").pack(side=tk.LEFT, padx=5)
        self.library_name_entry = ttk.Entry(bottom_frame)
        self.library_name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.library_name_entry.insert(0, "dbc_library")  # Default library name

        # Radio buttons for language selection
        self.language_var = tk.StringVar(value="c")  # Default: C++
        c_radio = ttk.Radiobutton(bottom_frame, text="C", variable=self.language_var, value="c")
        cpp_radio = ttk.Radiobutton(bottom_frame, text="C++", variable=self.language_var, value="cpp")
        c_radio.pack(side=tk.LEFT, padx=5)
        cpp_radio.pack(side=tk.LEFT, padx=5)

        # Button for selecting all items
        select_all_button = ttk.Button(bottom_frame, text="Select All", command=self.select_all)
        select_all_button.pack(side=tk.LEFT, padx=5)

        # Button for deselecting all items
        select_all_button = ttk.Button(bottom_frame, text="Deselect All", command=self.deselect_all)
        select_all_button.pack(side=tk.LEFT, padx=5)

        # Button for generating library
        generate_button = ttk.Button(bottom_frame, text="Generate Library", command=self.generate_library)
        generate_button.pack(side=tk.LEFT, padx=5)

    def open_files(self):
        """Open multiple DBC files and load their content into the CheckboxTreeview."""
        file_paths = filedialog.askopenfilenames(
            title="Select DBC files",
            filetypes=[("DBC files", "*.dbc")])  # Select .dbc files only
        if file_paths:
            shortened_file_paths = [os.path.basename(file_path) for file_path in file_paths]
            self.label.config(text=f"Selected files: {', '.join(shortened_file_paths)}")
            self.dbs.clear()  # Clear previously loaded databases
            self.tree.delete(*self.tree.get_children())  # Clear the CheckboxTreeview

            for file_path in file_paths:
                try:
                    # Load DBC file using cantools
                    db = cantools.database.load_file(file_path)
                    self.dbs.append(db)

                    # Add messages and signals to the CheckboxTreeview
                    for message in db.messages:
                        message_id = self.tree.insert("", "end", text=message.name, values=("Message", message.frame_id))
                        for signal in message.signals:
                            self.tree.insert(message_id, "end", text=signal.name, values=("Signal", signal.start))

                except Exception as e:
                    messagebox.showerror("Error", f"Can't read DBC file {file_path}: {e}")

    def select_all(self):
        """Select all items in the CheckboxTreeview."""
        for item in self.tree.get_children():
            self.tree.change_state(item, "checked")  # Select message
            for child in self.tree.get_children(item):
                self.tree.change_state(child, "checked")  # Select signal

    def deselect_all(self):
        """Select all items in the CheckboxTreeview."""
        for item in self.tree.get_children():
            self.tree.change_state(item, "unchecked")  # Select message
            for child in self.tree.get_children(item):
                self.tree.change_state(child, "unchecked")  # Select signal

    def generate_library(self):
        """Generate C++ library from selected messages and signals."""
        selected_items = self.tree.get_checked()  # Get all checked items
        if not selected_items:
            messagebox.showwarning("Warning", "No items selected for generation.")
            return

        if not self.dbs:
            messagebox.showwarning("Warning", "No DBC files loaded.")
            return

        # Get the library name from the entry
        library_name = self.library_name_entry.get().strip()
        if not library_name:
            library_name = "dbc_library"  # Default name if the entry is empty

        # Ask the user to select a directory
        directory = filedialog.askdirectory(
            title="Select directory to save the library"
        )
        if not directory:  # User canceled the dialog
            return

        # Get selected language (C or C++)
        language = self.language_var.get()

        if language == "c":
            # Generate C header and implementation files
            h_code, c_code = self.generate_c_code(selected_items, library_name)

            # Save generated header file
            h_file_path = os.path.join(directory, f"{library_name}.h")
            with open(h_file_path, "w") as h_file:
                h_file.write(h_code)
            messagebox.showinfo("Success", f"Generated {library_name} in {h_file_path}")

            # Save generated implementation file
            c_file_path = os.path.join(directory, f"{library_name}.c")
            with open(c_file_path, "w") as c_file:
                c_file.write(c_code)
            messagebox.showinfo("Success", f"Generated {library_name} in {c_file_path}")

        else:
            # Generate C++ header and implementation files
            hpp_code, cpp_code = self.generate_cpp_code(selected_items, library_name)

            # Save generated header file
            hpp_file_path = os.path.join(directory, f"{library_name}.hpp")
            with open(hpp_file_path, "w") as hpp_file:
                hpp_file.write(hpp_code)
            messagebox.showinfo("Success", f"Generated {library_name} in {hpp_file_path}")

            # Save generated implementation file
            cpp_file_path = os.path.join(directory, f"{library_name}.cpp")
            with open(cpp_file_path, "w") as cpp_file:
                cpp_file.write(cpp_code)
            messagebox.showinfo("Success", f"Generated {library_name} in {cpp_file_path}")

    def generate_cpp_code(self, selected_items, library_name):
        """Generate C++ code for selected messages and signals."""
        # Generate C++ header file (.hpp)
        hpp_code = f"// Generated C++ library header for {library_name}\n\n"
        hpp_code += f"#ifndef {library_name.upper()}_HPP\n"
        hpp_code += f"#define {library_name.upper()}_HPP\n\n"
        hpp_code += "#include <string>\n"
        hpp_code += "#include <vector>\n\n"

        # Define the DBCSignal structure
        hpp_code += "// Structure for signal\n"
        hpp_code += "struct DBCSignal {\n"
        hpp_code += "    std::string name;\n"
        hpp_code += "    int startBit;\n"
        hpp_code += "    int length;\n"
        hpp_code += "    std::string byteOrder;\n"
        hpp_code += "    char valueType;\n"
        hpp_code += "    double factor;\n"
        hpp_code += "    double offset;\n"
        hpp_code += "    double min;\n"
        hpp_code += "    double max;\n"
        hpp_code += "    std::string unit;\n"
        hpp_code += "    std::string receiver;\n"
        hpp_code += "\n"
        hpp_code += "    // Constructor\n"
        hpp_code += "    DBCSignal(std::string n, int start, int len, std::string byteOrder, char valueType, "
        hpp_code += "double factor, double offset, double min = 0.0, double max = 0.0, "
        hpp_code += "std::string unit = \"\", std::string receiver = \"\")\n"
        hpp_code += "        : name(n), startBit(start), length(len), byteOrder(byteOrder), valueType(valueType), "
        hpp_code += "factor(factor), offset(offset), min(min), max(max), unit(unit), receiver(receiver) {}\n"
        hpp_code += "};\n\n"

        # Define the DBCMessage structure
        hpp_code += "// Structure for message\n"
        hpp_code += "struct DBCMessage {\n"
        hpp_code += "    int id;\n"
        hpp_code += "    std::string name;\n"
        hpp_code += "    int dlc;\n"
        hpp_code += "    std::string sender;\n"
        hpp_code += "    std::vector<DBCSignal> signals;\n"
        hpp_code += "};\n\n"

        # Declare messages in the header file
        hpp_code += "// Message declaration\n"
        selected_messages = defaultdict(list)  # Dictionary to store selected messages and their signals
        for item in selected_items:
            item_type = self.tree.item(item, "values")[0]
            if item_type == "Message":
                message_name = self.tree.item(item, "text")
                selected_messages[message_name] = []  # Select all signals if the message is selected
            elif item_type == "Signal":
                parent = self.tree.parent(item)
                message_name = self.tree.item(parent, "text")
                signal_name = self.tree.item(item, "text")
                selected_messages[message_name].append(signal_name)

        for message_name in selected_messages:
            hpp_code += f"extern DBCMessage {message_name};\n"

        hpp_code += f"\n#endif // {library_name.upper()}_HPP\n"

        # Generate C++ implementation file (.cpp)
        cpp_code = f"// Generated C++ library implementation for {library_name}\n\n"
        cpp_code += f'#include "{library_name}.hpp"\n\n'

        # Define messages in the implementation file
        cpp_code += "// Definition of messages and signals\n"
        for message_name, signal_names in selected_messages.items():
            # Find the message in the loaded databases
            message = None
            for db in self.dbs:
                try:
                    message = db.get_message_by_name(message_name)
                    break
                except KeyError:
                    continue

            if not message:
                continue  # Skip if the message is not found

            cpp_code += f"// Message: {message.name}\n"
            cpp_code += f"DBCMessage {message.name} = {{\n"
            cpp_code += f"    {message.frame_id},\n"
            cpp_code += f"    \"{message.name}\",\n"
            cpp_code += f"    {message.length},\n"
            cpp_code += f"    \"{message.senders[0] if message.senders else ''}\",\n"
            cpp_code += "    {\n"

            for signal in message.signals:
                if not signal_names or signal.name in signal_names:  # Add only selected signals
                    min_value = signal.minimum if signal.minimum is not None else 0.0
                    max_value = signal.maximum if signal.maximum is not None else 0.0

                    cpp_code += "        DBCSignal{\n"
                    cpp_code += f"            \"{signal.name}\",\n"
                    cpp_code += f"            {signal.start},\n"
                    cpp_code += f"            {signal.length},\n"
                    cpp_code += f"            \"{'big_endian' if signal.byte_order == 'big_endian' else 'little_endian'}\",\n"
                    cpp_code += f"            '{'s' if signal.is_signed else 'u'}',\n"
                    cpp_code += f"            {signal.scale},\n"
                    cpp_code += f"            {signal.offset},\n"
                    cpp_code += f"            {min_value},\n"
                    cpp_code += f"            {max_value},\n"
                    cpp_code += f"            \"{signal.unit}\",\n"
                    cpp_code += f"            \"{', '.join(signal.receivers) if signal.receivers else 'None'}\"\n"
                    cpp_code += "        },\n"

            cpp_code += "    }\n"
            cpp_code += "};\n\n"

        return hpp_code, cpp_code

    def generate_c_code(self, selected_items, library_name):
        """Generate C code for selected messages and signals."""
        # Generate C header file (.h)
        h_code = f"// Generated C library header for {library_name}\n\n"
        h_code += f"#ifndef {library_name.upper()}_H\n"
        h_code += f"#define {library_name.upper()}_H\n\n"
        h_code += "#include <stdint.h>\n"
        h_code += "#include <stddef.h>\n\n"

        # Define the DBCSignal structure
        h_code += "// Structure for signal\n"
        h_code += "typedef struct {\n"
        h_code += "    const char *name;\n"
        h_code += "    int startBit;\n"
        h_code += "    int length;\n"
        h_code += "    const char *byteOrder;\n"
        h_code += "    char valueType;\n"
        h_code += "    double factor;\n"
        h_code += "    double offset;\n"
        h_code += "    double min;\n"
        h_code += "    double max;\n"
        h_code += "    const char *unit;\n"
        h_code += "    const char *receiver;\n"
        h_code += "} DBCSignal;\n\n"

        # Define the DBCMessage structure
        h_code += "// Structure for message\n"
        h_code += "typedef struct {\n"
        h_code += "    int id;\n"
        h_code += "    const char *name;\n"
        h_code += "    int dlc;\n"
        h_code += "    const char *sender;\n"
        h_code += "    size_t num_signals;\n"
        h_code += "    DBCSignal *signals;\n"
        h_code += "} DBCMessage;\n\n"

        # Declare messages in the header file
        h_code += "// Message declaration\n"
        selected_messages = defaultdict(list)
        for item in selected_items:
            item_type = self.tree.item(item, "values")[0]
            if item_type == "Message":
                message_name = self.tree.item(item, "text")
                selected_messages[message_name] = []
            elif item_type == "Signal":
                parent = self.tree.parent(item)
                message_name = self.tree.item(parent, "text")
                signal_name = self.tree.item(item, "text")
                selected_messages[message_name].append(signal_name)

        for message_name in selected_messages:
            h_code += f"extern DBCMessage {message_name};\n"

        h_code += f"\n#endif // {library_name.upper()}_H\n"

        # Generate C implementation file (.c)
        c_code = f"// Generated C library implementation for {library_name}\n\n"
        c_code += f'#include "{library_name}.h"\n\n'

        # Define messages in the implementation file
        c_code += "// Definition of messages and signals\n"
        for message_name, signal_names in selected_messages.items():
            message = None
            for db in self.dbs:
                try:
                    message = db.get_message_by_name(message_name)
                    break
                except KeyError:
                    continue

            if not message:
                continue

            c_code += f"// Message: {message.name}\n"

            # Check if the message has any signals
            if message.signals:
                # Define signals array only if the message has signals
                c_code += f"static DBCSignal {message.name}_signals[] = {{\n"
                for signal in message.signals:
                    if not signal_names or signal.name in signal_names:
                        min_value = signal.minimum if signal.minimum is not None else 0.0
                        max_value = signal.maximum if signal.maximum is not None else 0.0
                        unit_value = f"\"{signal.unit}\"" if signal.unit else "NULL"
                        receiver_value = f"\"{', '.join(signal.receivers)}\"" if signal.receivers else "NULL"

                        c_code += "    {\n"
                        c_code += f"        .name = \"{signal.name}\",\n"
                        c_code += f"        .startBit = {signal.start},\n"
                        c_code += f"        .length = {signal.length},\n"
                        c_code += f"        .byteOrder = \"{'big_endian' if signal.byte_order == 'big_endian' else 'little_endian'}\",\n"
                        c_code += f"        .valueType = '{'s' if signal.is_signed else 'u'}',\n"
                        c_code += f"        .factor = {signal.scale},\n"
                        c_code += f"        .offset = {signal.offset},\n"
                        c_code += f"        .min = {min_value},\n"
                        c_code += f"        .max = {max_value},\n"
                        c_code += f"        .unit = {unit_value},\n"
                        c_code += f"        .receiver = {receiver_value}\n"
                        c_code += "    },\n"
                c_code += "};\n\n"

                # Set num_signals based on the number of signals
                num_signals = len(message.signals)
            else:
                # If there are no signals, set num_signals to 0
                num_signals = 0
                c_code += "// No signals for this message\n"

            # Define message structure
            sender_value = f"\"{message.senders[0]}\"" if message.senders else "NULL"

            c_code += f"DBCMessage {message.name} = {{\n"
            c_code += f"    .id = {message.frame_id},\n"
            c_code += f"    .name = \"{message.name}\",\n"
            c_code += f"    .dlc = {message.length},\n"
            c_code += f"    .sender = {sender_value},\n"
            c_code += f"    .num_signals = {num_signals},\n"  # Use calculated num_signals
            c_code += f"    .signals = {message.name}_signals\n" if message.signals else "    .signals = NULL\n"
            c_code += "};\n\n"

        return h_code, c_code


if __name__ == '__main__':
    # Create main window
    root = tk.Tk()

    # Initialize the application
    app = DBCLibraryGenerator(root)

    # Run app
    root.mainloop()