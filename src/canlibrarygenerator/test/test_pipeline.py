import os
import subprocess
import shutil
import sys

from src.canlibrarygenerator.generate_functions.generate_c_library import generate_c_code
from src.canlibrarygenerator.generate_functions.generate_cpp_library import generate_cpp_code
from src.canlibrarygenerator.scripts.codegen_utils import generate_all_code
from src.canlibrarygenerator.scripts.delete_temp_files import delete_temp_files


def run_and_check(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print("❌ Command failed:")
        print(" ".join(cmd))
        print("\nSTDOUT:\n", result.stdout)
        print("\nSTDERR:\n", result.stderr)
        sys.exit(1)

    return result


def compile_and_run(executable):
    run = subprocess.run([executable], capture_output=True, text=True)

    print("Program output:\n", run.stdout)

    if run.returncode != 0:
        print("❌ Runtime error:\n", run.stderr)
        sys.exit(1)

    print("✅ Execution OK\n")


# ---------------- CONFIG ----------------

dbc_file = os.path.join(os.path.dirname(__file__), '..', 'dbc', 'CAN_example.dbc')
output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'temp'))
test_dir = os.path.abspath(os.path.dirname(__file__))
library_name = "cangen"


# ---------------- GENERATION ----------------

print("🔧 Generating code...")
generate_all_code(dbc_file, library_name, generate_c_code, generate_cpp_code)

c_dir = os.path.join(output_dir, library_name)


# ---------------- TOOL CHECK ----------------

if shutil.which("gcc") is None:
    print("Error: gcc not found")
    sys.exit(1)

if shutil.which("g++") is None:
    print("Error: g++ not found")
    sys.exit(1)


# ---------------- MOCK (FAULT-PROOF) ----------------

mock_file = os.path.join(output_dir, "mock.c")

with open(mock_file, "w") as f:
    f.write(f"""
#include "{library_name}_db.h"

void {library_name}_msg_send(const can_db_msg_t* msg)
{{
    (void)msg;
}}
""")


# ---------------- C TEST ----------------

print("🔨 Compiling C test...")

c_test_file = os.path.join(test_dir, "test_c.c")
c_exec = os.path.join(output_dir, "test_c.exe")

run_and_check([
    "gcc",
    c_test_file,
    os.path.join(c_dir, f"{library_name}_interface.c"),
    os.path.join(c_dir, f"{library_name}_db.c"),
    mock_file,
    "-I", c_dir,
    "-o", c_exec,
    "-lm"
])

compile_and_run(c_exec)


# ---------------- C++ TEST ----------------

print("🔨 Compiling C++ test...")

cpp_test_file = os.path.join(test_dir, "test_cpp.cpp")
cpp_exec = os.path.join(output_dir, "test_cpp.exe")

run_and_check([
    "g++",
    cpp_test_file,
    os.path.join(output_dir, f"{library_name}.cpp"),
    "-I", output_dir,
    "-o", cpp_exec
])

compile_and_run(cpp_exec)


# ---------------- CLEANUP ----------------

delete_temp_files()

print("🎉 ALL TESTS PASSED")