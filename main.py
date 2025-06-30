import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from ttkwidgets import CheckboxTreeview
import cantools
import os
from generate_functions.generate_c_library import generate_c_code
from generate_functions.generate_cpp_library import generate_cpp_code

# Define your app version
__version__ = "0.2.0"


class DBCLibraryGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("Library generator for DBC files")
        self.dbs = []  # List of loaded DBC databases
        self.tree = None  # CheckboxTreeview for messages and signals
        self.files = None  # Label for selected files
        self.version = None # Label for version
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
        self.files = ttk.Label(file_frame, text="No files selected.", foreground="gray")
        self.files.pack(side=tk.LEFT, padx=10)

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

        # Label for app version
        self.version = ttk.Label(root, text=f"App version {__version__}", foreground="gray")
        self.version.pack(side=tk.RIGHT, padx=10)

    def open_files(self):
        """Open multiple DBC files and load their content into the CheckboxTreeview."""
        file_paths = filedialog.askopenfilenames(
            title="Select DBC files",
            filetypes=[("DBC files", "*.dbc")])  # Select .dbc files only
        if file_paths:
            shortened_file_paths = [os.path.basename(file_path) for file_path in file_paths]
            self.files.config(text=f"Selected files: {', '.join(shortened_file_paths)}")
            self.dbs.clear()  # Clear previously loaded databases
            self.tree.delete(*self.tree.get_children())  # Clear the CheckboxTreeview

            for file_path in file_paths:
                try:
                    # Load DBC file using cantools
                    db = cantools.database.load_file(file_path)
                    self.dbs.append(db)

                    # Add messages and signals to the CheckboxTreeview
                    for message in db.messages:
                        message_id = self.tree.insert("", "end", text=message.name, values=("Message", hex(message.frame_id)))
                        for signal in message.signals:
                            self.tree.insert(message_id, "end", text=signal.name, values="Signal")

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
            h_code, c_code = generate_c_code(selected_items, library_name, self.dbs, self.tree)

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
            hpp_code, cpp_code = generate_cpp_code(selected_items, library_name, self.dbs, self.tree)

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


if __name__ == '__main__':
    # Create main window
    root = tk.Tk()

    # Initialize the application
    app = DBCLibraryGenerator(root)

    # Run app
    root.mainloop()