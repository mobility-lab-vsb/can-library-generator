import os
import cantools
import shutil
import sys
from src.canlibrarygenerator.generate_functions.generate_c_library import generate_c_code
from src.canlibrarygenerator.generate_functions.generate_cpp_library import generate_cpp_code
from collections import namedtuple

# Configuration
dbc_path = os.path.join(os.path.dirname(__file__), '..', 'dbc', 'CAN_example.dbc')
dbc_path = os.path.abspath(dbc_path)
library_name = "dbc_library_test"
output_dir = os.path.join(os.path.dirname(__file__), '..', 'temp')
if os.path.exists(output_dir):
    shutil.rmtree(output_dir)
os.makedirs(output_dir, exist_ok=True)

test_dir = os.path.abspath(os.path.dirname(__file__))

if os.path.exists(output_dir):
    shutil.rmtree(output_dir)
os.makedirs(output_dir, exist_ok=True)

# Mock database
dbc_dbs = []

try:
    db = cantools.db.load_file(dbc_path)
    dbc_dbs.append(db)
except Exception as e:
    print("Error", f"Can't read DBC file {dbc_path}: {e}")
    sys.exit(1)


# Mock structure for tree type (represents GUI tree)
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

# Mock tree
class MockTree:
    def item(self, item_id, option):
        if option == "values":
            return [item_id.type]
        if option == "text":
            return item_id.name

    def parent(self, item_id):
        return SelectedItem("Message", item_id.parent, None)

tree = MockTree()

# Generate C library
try:
    h_code, c_code = generate_c_code(selected_items, library_name, dbc_dbs, tree)
except Exception as e:
    print(f"Error during C code generation: {e}")
    sys.exit(1)

os.makedirs(output_dir, exist_ok=True)
with open(f"{output_dir}/{library_name}.h", "w") as f:
    f.write(h_code)
with open(f"{output_dir}/{library_name}.c", "w") as f:
    f.write(c_code)

# Generate C++ library
try:
    hpp_code, cpp_code = generate_cpp_code(selected_items, library_name, dbc_dbs, tree)
except Exception as e:
    print(f"Error during C++ code generation: {e}")
    sys.exit(1)

with open(f"{output_dir}/{library_name}.hpp", "w") as f:
    f.write(hpp_code)
with open(f"{output_dir}/{library_name}.cpp", "w") as f:
    f.write(cpp_code)

# Test if GCC and G++ are installed
if shutil.which("gcc") is None:
    print("Error: 'gcc' not found. Please install GCC and make sure it's in your PATH.")
    sys.exit(1)

if shutil.which("g++") is None:
    print("Error: 'g++' not found. Please install GCC and make sure it's in your PATH.")
    sys.exit(1)