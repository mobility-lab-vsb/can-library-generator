import os
import subprocess
import shutil
import sys
from src.canlibrarygenerator.generate_functions.generate_c_library import generate_c_code
from src.canlibrarygenerator.generate_functions.generate_cpp_library import generate_cpp_code
from src.canlibrarygenerator.scripts.codegen_utils import generate_all_code
from src.canlibrarygenerator.scripts.delete_temp_files import delete_temp_files


def test_compilation(result, comp_exec):
    if result.returncode == 0:
        run = subprocess.run([comp_exec], capture_output=True, text=True)
        print("Program output:\n", run.stdout)
        if run.returncode != 0:
            print(f"Error: {run.stderr}")
            sys.exit(1)
        print("Compilation succeeded!\n")
    else:
        print("Compilation failed!\n")
        print(result.stderr)
        sys.exit(1)

# Configuration
dbc_file = os.path.join(os.path.dirname(__file__), '..', 'dbc', 'CAN_example.dbc')
output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'temp'))
test_dir = os.path.abspath(os.path.dirname(__file__))
library_name = "cangen"
generate_all_code(dbc_file, library_name, generate_c_code, generate_cpp_code)

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
c_result = subprocess.run(["gcc", c_test_file, f"{output_dir}/cangen/{library_name}_interface.c", f"{output_dir}/cangen/{library_name}_db.c", "-I", output_dir, "-o", c_exec, "-lm"], capture_output=True, text=True)
test_compilation(c_result, c_exec)

# Compile and test C++ files
print("Compiling and testing C++ files...")
cpp_test_file = os.path.join(test_dir, "test_cpp.cpp")
cpp_exec = os.path.join(output_dir, "test_cpp.exe")
cpp_result = subprocess.run(["g++", cpp_test_file, f"{output_dir}/{library_name}.cpp", "-I", output_dir, "-o", cpp_exec], capture_output=True, text=True)
test_compilation(cpp_result, cpp_exec)

delete_temp_files()