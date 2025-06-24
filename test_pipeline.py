import subprocess
import cantools
import shutil
import sys
from generate_c_library import generate_c_code
from generate_cpp_library import generate_cpp_code
from collections import namedtuple

# Mock database
dbc_path = "dbc/STES_CANchasis.dbc"
dbc_dbs = []
try:
    db = cantools.db.load_file(dbc_path)
    dbc_dbs.append(db)
except Exception as e:
    print("Error", f"Can't read DBC file {dbc_path}: {e}")


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
    SelectedItem("Signal", "sigMO_Oil_pressure", "msgMotor_01")
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

# Initialize tree and set library name
tree = MockTree()
library_name = "dbc_library_test"

# Generate C library
h_code, c_code = generate_c_code(selected_items, library_name, dbc_dbs, tree)
with open(f"{library_name}.h", "w") as f:
    f.write(h_code)
with open(f"{library_name}.c", "w") as f:
    f.write(c_code)

# Generate C++ library
hpp_code, cpp_code = generate_cpp_code(selected_items, library_name, dbc_dbs, tree)
with open(f"{library_name}.hpp", "w") as f:
    f.write(hpp_code)
with open(f"{library_name}.cpp", "w") as f:
    f.write(cpp_code)

# Test if GCC and G++ are installed
if shutil.which("gcc") is None:
    print("Error: 'gcc' not found. Please install GCC and make sure it's in your PATH.")
    sys.exit(1)

if shutil.which("g++") is None:
    print("Error: 'g++' not found. Please install GCC and make sure it's in your PATH.")
    sys.exit(1)

# Compile C files
print("Compiling C files...")
c_result = subprocess.run(["gcc", f"{library_name}.c", "-c", "-o", f"{library_name}.o"], capture_output=True, text=True)
if c_result.returncode == 0:
    print("Compilation succeeded!\n")
else:
    print("Compilation failed!\n")
    print(c_result.stderr)

# Compile C++ files
print("Compiling C++ files...")
cpp_result = subprocess.run(["g++", f"{library_name}.cpp", "-c", "-o", f"{library_name}_cpp.o"], capture_output=True, text=True)
if cpp_result.returncode == 0:
    print("Compilation succeeded!\n")
else:
    print("Compilation failed!\n")
    print(cpp_result.stderr)