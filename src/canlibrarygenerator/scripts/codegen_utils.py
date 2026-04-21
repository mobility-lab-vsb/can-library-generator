import os
import sys
import shutil
import cantools
from collections import namedtuple


def generate_all_code(dbc_filename, library_name, generate_c_code, generate_cpp_code):
    """
    Generates both C and C++ libraries from a given DBC file.
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
        db.name = os.path.basename(dbc_path)
        dbc_dbs = [db]
    except Exception as e:
        print(f"Error: Can't read DBC file {dbc_path}: {e}")
        sys.exit(1)

    # --- Mock structures for testing (LEGACY SUPPORT) ---
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
        h_init, h_code, c_code, func_h, func_c = generate_c_code(
            selected_items,
            library_name,
            dbc_dbs,
            tree,
            __version__="dev"
        )
    except Exception as e:
        print(f"Error during C code generation: {e}")
        sys.exit(1)

    # --- Save C files ---
    c_dir = os.path.join(output_dir, library_name)
    os.makedirs(c_dir, exist_ok=True)

    c_files = {
        "can_db_def.h": h_init,
        f"{library_name}_db.h": h_code,
        f"{library_name}_db.c": c_code,
        f"{library_name}_interface.h": func_h,
        f"{library_name}_interface.c": func_c
    }

    for filename, content in c_files.items():
        with open(os.path.join(c_dir, filename), "w") as f:
            f.write(content)

    # --- Generate C++ code ---
    try:
        cpp_def, cpp_db_h, cpp_db_c, cpp_int_h, cpp_int_c = generate_cpp_code(
            selected_items,
            library_name,
            dbc_dbs,
            tree,
            __version__="dev"
        )
    except Exception as e:
        print(f"Error during C++ code generation: {e}")
        sys.exit(1)

    # --- Save C++ files mirroring C structure ---
    cpp_dir = os.path.join(output_dir, f"{library_name}_cpp")
    os.makedirs(cpp_dir, exist_ok=True)

    cpp_files = {
        "can_db_def.hpp": cpp_def,
        f"{library_name}_db.hpp": cpp_db_h,
        f"{library_name}_db.cpp": cpp_db_c,
        f"{library_name}_interface.hpp": cpp_int_h,
        f"{library_name}_interface.cpp": cpp_int_c
    }

    for filename, content in cpp_files.items():
        with open(os.path.join(cpp_dir, filename), "w") as f:
            f.write(content)