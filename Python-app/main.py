import tkinter as tk
from tkinter import filedialog, messagebox
import cantools

def open_file():
    file_path = filedialog.askopenfilename(
        title="Select file",
        filetypes=[("DBC files", "*.dbc")])  # Select .dbc files only
    if file_path:
        label.config(text=f"Selected file: {file_path}")

        try:
            # Load DBC file using cantools
            db = cantools.database.load_file(file_path)

            # Get list of nodes, messages, and signals
            nodes = db.nodes
            messages = db.messages
            signals = []

            for msg in messages:  # Access messages by their values
                signals.extend(msg.signals)  # Add signals for each message

            # Show info in GUI
            display_info(nodes, messages, signals)
        except Exception as e:
            messagebox.showerror("Error", f"Can't read DBC file: {e}")

def display_info(nodes, messages, signals):
    # Clean old info
    listbox_nodes.delete(0, tk.END)
    listbox_messages.delete(0, tk.END)
    listbox_signals.delete(0, tk.END)

    # Show nodes
    for node in nodes:
        listbox_nodes.insert(tk.END, node)

    # Show messages
    for message in messages:
        listbox_messages.insert(tk.END, message)

    # Show signals
    for signal in signals:
        listbox_signals.insert(tk.END, signal)

if __name__ == '__main__':
    # Create main window
    root = tk.Tk()
    root.title("Library generator for DBC files")

    # Button for open dialog
    button = tk.Button(root, text="Select DBC file", command=open_file)
    button.pack(pady=10)

    # Label for selected file
    label = tk.Label(root, text="No file selected.")
    label.pack(pady=10)

    # List of nodes
    label_nodes = tk.Label(root, text="Nodes:")
    label_nodes.pack(pady=5)
    listbox_nodes = tk.Listbox(root, height=10, width=50)
    listbox_nodes.pack(pady=5)

    # List of messages
    label_messages = tk.Label(root, text="Messages:")
    label_messages.pack(pady=5)
    listbox_messages = tk.Listbox(root, height=10, width=50)
    listbox_messages.pack(pady=5)

    # List of signals
    label_signals = tk.Label(root, text="Signals:")
    label_signals.pack(pady=5)
    listbox_signals = tk.Listbox(root, height=10, width=50)
    listbox_signals.pack(pady=5)

    # Run app
    root.mainloop()