import os
import subprocess
import shutil
import sys

from src.canlibrarygenerator.generate_functions.generate_c_library import generate_c_code
from src.canlibrarygenerator.generate_functions.generate_cpp_library import generate_cpp_code
from src.canlibrarygenerator.scripts.codegen_utils import generate_all_code
from src.canlibrarygenerator.scripts.delete_temp_files import delete_temp_files


def run_cmd(cmd, step_name):
    print(f"➜ Running: {step_name} ...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"❌ ERROR in step: {step_name}")
        print("Command:", " ".join(cmd))
        print("\n--- STDOUT ---\n", result.stdout)
        print("\n--- STDERR ---\n", result.stderr)
        sys.exit(1)

    return result


def execute_binary(executable_path, prefix=""):
    print(f"➜ Executing binary: {os.path.basename(executable_path)}")
    run = subprocess.run([executable_path], capture_output=True, text=True)

    indented_output = "\n".join([f"    {line}" for line in run.stdout.splitlines()])
    print(f"{indented_output}\n")

    if run.returncode != 0:
        print("❌ Runtime error:")
        print(run.stderr)
        sys.exit(1)


# ---------------- CONFIG ----------------
dbc_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'dbc', 'CAN_example.dbc'))
output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'temp'))
test_dir = os.path.abspath(os.path.dirname(__file__))
library_name = "cangen"

# ---------------- START ----------------
if __name__ == "__main__":
    print("🔧 1. Generating code from DBC...")
    generate_all_code(dbc_file, library_name, generate_c_code, generate_cpp_code)

    c_dir = os.path.join(output_dir, library_name)

    if not shutil.which("gcc") or not shutil.which("g++"):
        print("❌ Error: gcc or g++ not found in system PATH.")
        sys.exit(1)

    # ---------------- MOCK ----------------
    mock_file = os.path.join(output_dir, "mock.c")
    with open(mock_file, "w") as f:
        f.write(f"""
#include "{library_name}_db.h"
void {library_name}_msg_send(const can_db_msg_t* msg) {{
    (void)msg; // Dummy implementation for linking
}}
""")

    # ---------------- C TEST ----------------
    print("\n🔨 2. Compiling C code...")
    c_test_file = os.path.join(test_dir, "test_c.c")
    c_exec = os.path.join(output_dir, "test_c.exe" if os.name == "nt" else "test_c")

    run_cmd([
        "gcc",
        c_test_file,
        os.path.join(c_dir, f"{library_name}_interface.c"),
        os.path.join(c_dir, f"{library_name}_db.c"),
        mock_file,
        "-I", c_dir,
        "-o", c_exec,
        "-lm"
    ], "Compiling C tests")

    execute_binary(c_exec)

    # ---------------- C++ TEST ----------------
    print("🔨 3. Compiling C++ code...")
    cpp_test_file = os.path.join(test_dir, "test_cpp.cpp")
    cpp_exec = os.path.join(output_dir, "test_cpp.exe" if os.name == "nt" else "test_cpp")

    run_cmd([
        "g++",
        cpp_test_file,
        os.path.join(output_dir, f"{library_name}.cpp"),
        "-I", output_dir,
        "-o", cpp_exec
    ], "Compiling C++ tests")

    execute_binary(cpp_exec)

    # ---------------- CLEANUP ----------------
    print("🧹 4. Cleaning up temporary files...")
    delete_temp_files()

    print("✅ ALL TESTS PASSED SUCCESSFULLY")