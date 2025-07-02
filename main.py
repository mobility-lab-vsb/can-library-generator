import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from ttkwidgets import CheckboxTreeview
import cantools
import os
import sv_ttk

from generate_functions.generate_c_library import generate_c_code
from generate_functions.generate_cpp_library import generate_cpp_code

# Define your app version
__version__ = "v1.0.0"


class DBCLibraryGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("CAN Library Generator")
        self.dbs = []  # List of loaded DBC databases
        self.tree = None  # CheckboxTreeview for messages and signals
        self.files_label = None  # Label for selected files
        self.library_name_entry = None  # Entry for library name
        self.language_var = tk.StringVar(value="c") # Language selection variable
        self.setup_gui()

    def setup_gui(self):
        """Initialize the GUI components."""
        # Apply Sun Valley theme
        sv_ttk.set_theme("dark")

        # Configure main window grid layout
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.geometry("700x600")

        # --- Top Frame: File Selection ---
        file_frame = ttk.LabelFrame(self.root, text="DBC File Selection", padding=(20, 10))
        file_frame.grid(row=0, column=0, padx=10, sticky="ew")
        file_frame.grid_columnconfigure(1, weight=1)

        # Button for open dialog
        select_files_button = ttk.Button(file_frame, text="📂 Select DBC Files", command=self.open_files)
        select_files_button.grid(row=0, column=0, padx=(0, 10), pady=5, sticky="w")

        # Label for selected files
        self.files_label = ttk.Label(file_frame, text="No files selected.", foreground="gray")
        self.files_label.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # --- Middle Frame: CheckboxTreeview for Messages and Signals ---
        tree_frame = ttk.LabelFrame(self.root, text="Messages and Signals", padding=(20, 10))
        tree_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # CheckboxTreeview for messages and signals
        self.tree = CheckboxTreeview(tree_frame, columns=("Type", "ID"), show="tree headings")
        self.tree.heading("#0", text="Name", anchor="center")
        self.tree.heading("Type", text="Type", anchor="center")
        self.tree.heading("ID", text="ID", anchor="center")
        # Adjust column properties
        self.tree.column("#0", width=280, minwidth=150, stretch=tk.YES)
        self.tree.column("Type", width=100, anchor="center")
        self.tree.column("ID", width=100, anchor="center")
        self.tree.grid(row=0, column=0, sticky="nsew")

        # Scrollbars for the treeview
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=vsb.set)

        # --- Bottom Frame: Controls and Generation ---
        controls_frame = ttk.LabelFrame(self.root, text="Generation Settings", padding=(20, 10))
        controls_frame.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="ew")
        controls_frame.grid_columnconfigure(1, weight=1)

        # Library name entry
        ttk.Label(controls_frame, text="Library Name:").grid(row=0, column=0, padx=(0, 10), pady=5, sticky="w")
        self.library_name_entry = ttk.Entry(controls_frame)
        self.library_name_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.library_name_entry.insert(0, "dbc_library")

        # Language selections
        ttk.Label(controls_frame, text="Language:").grid(row=0, column=2, padx=(20, 5), pady=5, sticky="w")
        c_radio = ttk.Radiobutton(controls_frame, text="C", variable=self.language_var, value="c")
        cpp_radio = ttk.Radiobutton(controls_frame, text="CPP", variable=self.language_var, value="cpp")
        c_radio.grid(row=0, column=3, padx=(0, 5), pady=5, sticky="w")
        cpp_radio.grid(row=0, column=4, padx=(0, 5), pady=5, sticky="w")

        # Selection buttons
        action_buttons_frame = ttk.Frame(controls_frame)
        action_buttons_frame.grid(row=1, column=0, columnspan=5, pady=10)
        action_buttons_frame.grid_columnconfigure(0, weight=1)
        action_buttons_frame.grid_columnconfigure(1, weight=1)

        select_all_button = ttk.Button(action_buttons_frame, text="✅ Select All", command=self.select_all)
        select_all_button.grid(row=0, column=0, padx=5, sticky="e")

        deselect_all_button = ttk.Button(action_buttons_frame, text="❌ Deselect All", command=self.deselect_all)
        deselect_all_button.grid(row=0, column=1, padx=5, sticky="w")

        # Generate button
        generate_button = ttk.Button(controls_frame, text="🚀 Generate Library", command=self.generate_library, style="Accent.TButton")
        generate_button.grid(row=2, column=0, columnspan=5, pady=10)

        # --- Footer: App version ---
        version_frame = ttk.Frame(self.root, padding=(10, 5))
        version_frame.grid(row=3, column=0, sticky="ew")
        version_frame.grid_columnconfigure(0, weight=1)

        ttk.Label(version_frame, text=f"App version {__version__}", foreground="gray").grid(row=0, column=0, sticky="e")

    def open_files(self):
        """Open multiple DBC files and load their content into the CheckboxTreeview."""
        file_paths = filedialog.askopenfilenames(
            title="Select DBC files",
            filetypes=[("DBC files", "*.dbc")])  # Select .dbc files only
        if file_paths:
            shortened_file_paths = [os.path.basename(file_path) for file_path in file_paths]
            self.files_label.config(text=f"Selected files: {', '.join(shortened_file_paths)}")
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

        try:
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

        except Exception as e:
            messagebox.showerror("Generation Error", f"An error occurred during {library_name} generation: {e}")


if __name__ == '__main__':
    # Create main window
    root = tk.Tk()

    # Initialize the application
    app = DBCLibraryGenerator(root)

    # Run app
    root.mainloop()