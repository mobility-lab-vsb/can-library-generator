import os
import sys
import shutil
import cantools
from collections import namedtuple


def generate_all_code(dbc_filename, library_name, generate_c_code, generate_cpp_code):
    """
    Generates both C and C++ libraries from a given DBC file.

    Args:
        dbc_filename (str): Path to the DBC file.
        library_name (str): Name of the generated library (e.g., "cangen").
        generate_c_code (function): Function that generates C code.
        generate_cpp_code (function): Function that generates C++ code.

    Returns:
        nothing
    """

    # --- Paths setup ---
    dbc_path = os.path.abspath(dbc_filename)
    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'temp'))

    # --- Clean and recreate output directory ---
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    # --- Load DBC file ---
    try:
        db = cantools.database.load_file(dbc_path)
        dbc_dbs = [db]
    except Exception as e:
        print(f"Error: Can't read DBC file {dbc_path}: {e}")
        sys.exit(1)

    # --- Mock structures for testing ---
    SelectedItem = namedtuple("SelectedItem", ["type", "name", "parent"])

    selected_items = [
        SelectedItem("Message", "msgMotor_01", None),
        SelectedItem("Signal", "sigMO_CRC", "msgMotor_01"),
        SelectedItem("Signal", "sigMO_CTR", "msgMotor_01"),
        SelectedItem("Signal", "sigMO_MotorRunningStatus", "msgMotor_01"),
        SelectedItem("Signal", "sigMO_PedalPosition", "msgMotor_01"),
        SelectedItem("Signal", "sigMO_EngineSpeed", "msgMotor_01"),
        SelectedItem("Signal", "sigMO_EngineTorque", "msgMotor_01"),
        SelectedItem("Signal", "sigMO_Oil_Temperature", "msgMotor_01"),
        SelectedItem("Signal", "sigMO_Oil_pressure", "msgMotor_01"),
        SelectedItem("Message", "msgVD_GNSS_precision_position", None),
        SelectedItem("Signal", "sigVD_GNSS_LatitudeDegree", "msgVD_GNSS_precision_position"),
        SelectedItem("Signal", "sigVD_GNSS_LongitudeDegree", "msgVD_GNSS_precision_position"),
        SelectedItem("Signal", "sigVD_GNSS_heading", "msgVD_GNSS_precision_position")
    ]

    class MockTree:
        """Mock implementation of a GUI-like tree structure used for testing."""
        def item(self, item_id, option):
            if option == "values":
                return [item_id.type]
            if option == "text":
                return item_id.name

        def parent(self, item_id):
            return SelectedItem("Message", item_id.parent, None)

    tree = MockTree()

    # --- Generate C code ---
    try:
        h_init, h_code, c_code, func_h, func_c = generate_c_code(selected_items, library_name, dbc_dbs, tree)
    except Exception as e:
        print(f"Error during C code generation: {e}")
        sys.exit(1)

    c_dir = os.path.join(output_dir, library_name)
    os.makedirs(c_dir, exist_ok=True)

    with open(f"{c_dir}/can_db_def.h", "w") as f:
        f.write(h_init)
    with open(f"{c_dir}/{library_name}_db.h", "w") as f:
        f.write(h_code)
    with open(f"{c_dir}/{library_name}_db.c", "w") as f:
        f.write(c_code)
    with open(f"{c_dir}/{library_name}_interface.h", "w") as f:
        f.write(func_h)
    with open(f"{c_dir}/{library_name}_interface.c", "w") as f:
        f.write(func_c)

    # --- Generate C++ code ---
    try:
        hpp_code, cpp_code = generate_cpp_code(selected_items, library_name, dbc_dbs, tree)
    except Exception as e:
        print(f"Error during C++ code generation: {e}")
        sys.exit(1)

    with open(f"{output_dir}/{library_name}.hpp", "w") as f:
        f.write(hpp_code)
    with open(f"{output_dir}/{library_name}.cpp", "w") as f:
        f.write(cpp_code)