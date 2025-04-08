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
        # Windows size
        self.root.geometry("600x500")

        # Frame for file selection
        file_frame = ttk.Frame(self.root, padding=10)
        file_frame.pack(fill=tk.X)

        # Button for open dialog
        button = ttk.Button(file_frame, text="\U0001F5C1 Select DBC files", command=self.open_files)
        button.pack(side=tk.LEFT, padx=5)

        # Label for selected files
        self.label = ttk.Label(file_frame, text="No files selected.", foreground="gray")
        self.label.pack(side=tk.LEFT, padx=10)

        # Frame for CheckboxTreeview
        tree_frame = ttk.Frame(self.root, padding=10)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        # CheckboxTreeview for messages and signals
        self.tree = CheckboxTreeview(tree_frame, columns=("Type", "ID"), show="tree headings")
        self.tree.heading("#0", text="Name", anchor="w")
        self.tree.heading("Type", text="Type", anchor="center")
        self.tree.heading("ID", text="ID", anchor="center")
        self.tree.column("#0", width=250)
        self.tree.column("Type", width=100, anchor="center")
        self.tree.column("ID", width=100, anchor="center")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Frame for controls
        bottom_frame = ttk.Frame(self.root, padding=10)
        bottom_frame.pack(fill=tk.X)

        # Library name entry
        ttk.Label(bottom_frame, text="Library Name:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.library_name_entry = ttk.Entry(bottom_frame, font=("Arial", 10))
        self.library_name_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.library_name_entry.insert(0, "dbc_library")

        # Language selection
        self.language_var = tk.StringVar(value="c")
        lang_frame = ttk.Frame(bottom_frame)
        lang_frame.grid(row=0, column=2, padx=5, pady=5)

        ttk.Label(lang_frame, text="Language:").pack(side=tk.LEFT)
        c_radio = ttk.Radiobutton(lang_frame, text="C", variable=self.language_var, value="c")
        cpp_radio = ttk.Radiobutton(lang_frame, text="C++", variable=self.language_var, value="cpp")
        c_radio.pack(side=tk.LEFT, padx=5)
        cpp_radio.pack(side=tk.LEFT, padx=5)

        # Selection buttons
        action_frame = ttk.Frame(bottom_frame)
        action_frame.grid(row=1, column=0, columnspan=3, pady=10)

        select_all_button = ttk.Button(action_frame, text="\u2705 Select All", command=self.select_all, width=15)
        select_all_button.pack(side=tk.LEFT, padx=5)

        deselect_all_button = ttk.Button(action_frame, text="\u274E Deselect All", command=self.deselect_all, width=15)
        deselect_all_button.pack(side=tk.LEFT, padx=5)

        # Generate button
        generate_button = ttk.Button(bottom_frame, text="Generate Library", command=self.generate_library)
        generate_button.grid(row=2, column=0, columnspan=3, pady=10)

        # Configure layout
        bottom_frame.columnconfigure(1, weight=1)

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
        # Group selected messages and signals
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
        h_code += "    uint64_t raw_value;\n"
        h_code += "    double value;\n"
        h_code += "} DBCSignal;\n\n"

        # Base message structure for iteration
        h_code += "// Base message structure for iteration\n"
        h_code += "typedef struct {\n"
        h_code += "    uint32_t id;\n"
        h_code += "    const char *name;\n"
        h_code += "    uint8_t dlc;\n"
        h_code += "    const char *sender;\n"
        h_code += "    size_t num_signals;\n"
        h_code += "    DBCSignal *signals;\n"
        h_code += "} DBCMessageBase;\n\n"

        # Generate unique struct for each message
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

            struct_name = f"DBCMessage_{message_name.replace(' ', '')}"
            h_code += f"// Message: {message_name}\n"
            h_code += f"typedef struct {{\n"
            h_code += "    DBCMessageBase base;\n"

            # Add direct signal pointers
            for signal in message.signals:
                if not signal_names or signal.name in signal_names:
                    h_code += f"    DBCSignal *{signal.name};\n"

            h_code += f"}} {struct_name};\n\n"

        # Declare messages as extern
        h_code += "// Message declarations\n"
        for message_name in selected_messages:
            struct_name = f"DBCMessage_{message_name.replace(' ', '')}"
            h_code += f"extern {struct_name} {message_name};\n"

        # Message registry
        h_code += "\n// Message registry for iteration\n"
        h_code += "extern DBCMessageBase* const dbc_all_messages[];\n"
        h_code += "extern const size_t dbc_all_messages_count;\n\n"

        # Function
        h_code += "// Functions\n"
        h_code += "DBCMessageBase* dbc_find_message_by_id(uint32_t can_id);\n"
        h_code += "uint64_t dbc_extract_signal(const uint8_t* data, uint16_t startBit, uint8_t length, const char* byteOrder);\n"
        h_code += "int dbc_decode_message(uint32_t can_id, uint8_t dlc, const uint8_t* data);\n\n"

        h_code += f"#endif // {library_name.upper()}_H\n"

        # Generate C implementation file (.c)
        c_code = f"// Generated C library implementation for {library_name}\n\n"
        c_code += f'#include "{library_name}.h"\n\n'

        # Define messages and signals
        message_definitions = []
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

            struct_name = f"DBCMessage_{message_name.replace(' ', '')}"

            c_code += f"// Message: {message.name}\n"

            # Define signals array
            if message.signals:
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
                        c_code += f"        .receiver = {receiver_value},\n"
                        c_code += f"        .raw_value = 0\n"
                        c_code += "    },\n"
                c_code += "};\n\n"

                num_signals = len([s for s in message.signals if not signal_names or s.name in signal_names])
            else:
                num_signals = 0
                c_code += "// No signals for this message\n"

            # Define message struct
            senders = ', '.join(message.senders)
            sender_value = f"\"{senders}\"" if message.senders else "NULL"
            signals_array = f"{message.name}_signals" if num_signals > 0 else "NULL"

            c_code += f"{struct_name} {message.name} = {{\n"
            c_code += f"    .base = {{\n"
            c_code += f"        .id = {message.frame_id},\n"
            c_code += f"        .name = \"{message.name}\",\n"
            c_code += f"        .dlc = {message.length},\n"
            c_code += f"        .sender = {sender_value},\n"
            c_code += f"        .num_signals = {num_signals},\n"
            c_code += f"        .signals = {signals_array}\n"
            c_code += f"    }},\n"

            # Assign direct pointers to signals
            for i, signal in enumerate(message.signals):
                if not signal_names or signal.name in signal_names:
                    c_code += f"    .{signal.name} = &{message.name}_signals[{i}],\n"

            c_code += "};\n\n"
            message_definitions.append(f"(DBCMessageBase*)&{message.name}")

        # Message registry
        c_code += "// Message registry\n"
        c_code += f"DBCMessageBase* const dbc_all_messages[] = {{\n    "
        c_code += ",\n    ".join(message_definitions)
        c_code += "\n};\n\n"
        c_code += f"const size_t dbc_all_messages_count = {len(message_definitions)};\n\n"

        # Find message function
        c_code += """// Find message by CAN ID
DBCMessageBase* dbc_find_message_by_id(uint32_t can_id) {
    for (size_t i = 0; i < dbc_all_messages_count; i++) {
        if (dbc_all_messages[i]->id == can_id) {
            return dbc_all_messages[i];
        }
    }
    return NULL;
}
\n"""

        # Extract signal function
        c_code +="""// Extract signal function
uint64_t dbc_extract_signal(const uint8_t* data, uint16_t startBit, uint8_t length, const char* byteOrder) {
    uint64_t result = 0;

    if (strcmp(byteOrder, "little_endian") == 0) {
        // Intel (little endian)
        int byteIndex = startBit / 8;
        int bitIndex = startBit % 8;
        int bitsLeft = length;
        int shift = 0;

        while (bitsLeft > 0) {
            uint8_t byte = data[byteIndex];
            int bitsInThisByte = (bitsLeft < (8 - bitIndex)) ? bitsLeft : (8 - bitIndex);
            uint8_t mask = ((1 << bitsInThisByte) - 1) << bitIndex;
            uint8_t bits = (byte & mask) >> bitIndex;
            result |= ((uint64_t)bits << shift);

            bitsLeft -= bitsInThisByte;
            shift += bitsInThisByte;
            byteIndex++;
            bitIndex = 0;
        }

    }
    else {
        // Motorola (big endian)
        for (int i = 0; i < length; i++) {
            int bitPos = startBit - i;
            int byteIndex = bitPos / 8;
            int bitIndex = bitPos % 8;
            uint8_t bit = (data[byteIndex] >> (7 - bitIndex)) & 0x1;
            result = (result << 1) | bit;
        }
    }

    return result;
}
\n"""

        # Decode message function
        c_code += """// Decode CAN message
int dbc_decode_message(uint32_t can_id, uint8_t dlc, const uint8_t* data) {
    DBCMessageBase* msg = dbc_find_message_by_id(can_id);
    if (!msg || msg->dlc != dlc) {
        printf("Message not found!\\n");
        return -1;
    }

    printf("Message found!\\n");

    for (size_t i = 0; i < msg->num_signals; i++) {
        DBCSignal* sig = &msg->signals[i];

        // Extract raw value
        sig->raw_value = dbc_extract_signal(data, sig->startBit, sig->length, sig->byteOrder);

        // Exchange to physical value
        sig->value = (sig->raw_value * sig->factor) + sig->offset;

        // Debug print signal values
        //printf("%s : %.2f\\n", sig->name, sig->value);
        //printf("(%llu * %.2f) + %.2f = %.2f\\n",
            //sig->raw_value, sig->factor, sig->offset, sig->value);
    }

    return 0;
}
\n"""
        return h_code, c_code


if __name__ == '__main__':
    # Create main window
    root = tk.Tk()

    # Initialize the application
    app = DBCLibraryGenerator(root)

    # Run app
    root.mainloop()