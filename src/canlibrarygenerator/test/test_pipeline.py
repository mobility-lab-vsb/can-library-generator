import os
import subprocess
import cantools
import shutil
import sys
from src.canlibrarygenerator.generate_functions.generate_c_library import generate_c_code
from src.canlibrarygenerator.generate_functions.generate_cpp_library import generate_cpp_code
from collections import namedtuple

# Configuration
dbc_path = os.path.join(os.path.dirname(__file__), '..', 'dbc', 'CAN_example.dbc')
dbc_path = os.path.abspath(dbc_path)
library_name = "cangen"
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

# Compile and test C files
print("Compiling and testing C files...")
c_test_file = os.path.join(test_dir, "test_c.c")
c_exec = os.path.join(output_dir, "test_c.exe")
c_result = subprocess.run(["gcc", c_test_file, f"{output_dir}/{library_name}.c", "-I", output_dir, "-o", c_exec], capture_output=True, text=True)
if c_result.returncode == 0:
    c_run = subprocess.run([c_exec], capture_output=True, text=True)
    print("Program output:\n", c_run.stdout)
    if c_run.returncode != 0:
        print(f"Error: {c_run.stderr}")
        sys.exit(1)
    print("Compilation succeeded!\n")
else:
    print("Compilation failed!\n")
    print(c_result.stderr)
    sys.exit(1)

# Compile and test C++ files
print("Compiling and testing C++ files...")
cpp_test_file = os.path.join(test_dir, "test_cpp.cpp")
cpp_exec = os.path.join(output_dir, "test_cpp.exe")
cpp_result = subprocess.run(["g++", cpp_test_file, f"{output_dir}/{library_name}.cpp", "-I", output_dir, "-o", cpp_exec], capture_output=True, text=True)
if cpp_result.returncode == 0:
    cpp_run = subprocess.run([cpp_exec], capture_output=True, text=True)
    print("Program output:\n", cpp_run.stdout)
    if cpp_run.returncode != 0:
        print(f"Error: {cpp_run.stderr}")
        sys.exit(1)
    print("Compilation succeeded!\n")
else:
    print("Compilation failed!\n")
    print(cpp_result.stderr)
    sys.exit(1)

for filename in os.listdir(output_dir):
    file_path = os.path.join(output_dir, filename)
    try:
        if os.path.isfile(file_path) or os.path.islink(file_path):
            os.remove(file_path)
        elif os.path.isdir(file_path):
            shutil.rmtree(file_path)
        print(f"Removing {file_path}...")
    except Exception as e:
        print(f"Error removing {file_path}: {e}")

if os.path.exists(output_dir):
    shutil.rmtree(output_dir)
    print(f"Removing {output_dir}...")