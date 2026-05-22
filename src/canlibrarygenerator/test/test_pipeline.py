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


def generate_variant(embedded: bool, suffix: str, with_units: bool = False):
    label_parts = ["embedded" if embedded else "normal"]

    if with_units:
        label_parts.append("units")

    label = " + ".join(label_parts)

    print(f"\n🔧 Generating {label} code from DBC...")

    generate_all_code(
        dbc_file,
        library_name,
        generate_c_code,
        generate_cpp_code,
        embedded=embedded,
        output_suffix=suffix,
        with_units=with_units
    )

def create_c_mock(c_dir: str):
    """
    Creates dummy send function for C linking.
    C++ test already has dummy implementation inside test_cpp.cpp.
    """
    mock_file = os.path.join(c_dir, "mock.c")

    with open(mock_file, "w", encoding="utf-8") as f:
        f.write(f"""
#include "{library_name}_db.h"

void {library_name}_msg_send(const can_db_msg_t* msg)
{{
    (void)msg; // Dummy implementation for linking
}}
""")

    return mock_file


def executable_name(base_name: str):
    return f"{base_name}.exe" if os.name == "nt" else base_name


def compile_and_run_c(folder_name: str, exe_base_name: str):
    c_dir = os.path.join(output_dir, folder_name)

    if not os.path.isdir(c_dir):
        print(f"❌ Error: C output directory not found: {c_dir}")
        sys.exit(1)

    mock_file = create_c_mock(c_dir)

    c_test_file = os.path.join(test_dir, "test_c.c")
    c_exec = os.path.join(output_dir, executable_name(exe_base_name))

    print(f"\n🔨 Compiling C tests for: {folder_name}")

    run_cmd([
        "gcc",
        "-std=c99",
        "-Wall",
        "-Wextra",
        c_test_file,
        os.path.join(c_dir, f"{library_name}_interface.c"),
        os.path.join(c_dir, f"{library_name}_db.c"),
        mock_file,
        "-I", c_dir,
        "-o", c_exec,
        "-lm"
    ], f"Compiling C tests ({folder_name})")

    execute_binary(c_exec)


def compile_and_run_cpp(folder_name: str, exe_base_name: str):
    cpp_dir = os.path.join(output_dir, folder_name)

    if not os.path.isdir(cpp_dir):
        print(f"❌ Error: C++ output directory not found: {cpp_dir}")
        sys.exit(1)

    cpp_test_file = os.path.join(test_dir, "test_cpp.cpp")
    cpp_exec = os.path.join(output_dir, executable_name(exe_base_name))

    print(f"\n🔨 Compiling C++ tests for: {folder_name}")

    run_cmd([
        "g++",
        "-std=c++17",
        "-Wall",
        "-Wextra",
        cpp_test_file,
        os.path.join(cpp_dir, f"{library_name}_interface.cpp"),
        os.path.join(cpp_dir, f"{library_name}_db.cpp"),
        "-I", cpp_dir,
        "-o", cpp_exec
    ], f"Compiling C++ tests ({folder_name})")

    execute_binary(cpp_exec)

# ---------------- START ----------------

if __name__ == "__main__":
    print("🧹 0. Cleaning temp directory...")

    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    os.makedirs(output_dir, exist_ok=True)

    if not shutil.which("gcc") or not shutil.which("g++"):
        print("❌ Error: gcc or g++ not found in system PATH.")
        sys.exit(1)

    # ---------------- GENERATION ----------------
    print("\n🔧 1. Generating normal library...")
    generate_variant(embedded=False, suffix="")

    print("\n🔧 2. Generating normal library with unit signal names...")
    generate_variant(
        embedded=False,
        suffix="_units",
        with_units=True
    )

    print("\n🔧 3. Generating embedded library...")
    generate_variant(embedded=True, suffix="_embedded")

    # ---------------- NORMAL C TEST ----------------
    print("\n🧪 4. Testing normal C library...")
    compile_and_run_c(
        folder_name=library_name,
        exe_base_name="test_c_normal"
    )

    # ---------------- NORMAL C++ TEST ----------------
    print("\n🧪 5. Testing normal C++ library...")
    compile_and_run_cpp(
        folder_name=f"{library_name}_cpp",
        exe_base_name="test_cpp_normal"
    )

    # ---------------- NORMAL + UNITS C TEST ----------------
    print("\n🧪 6. Testing normal C library with unit signal names...")
    compile_and_run_c(
        folder_name=f"{library_name}_units",
        exe_base_name="test_c_units"
    )

    # ---------------- NORMAL + UNITS C++ TEST ----------------
    print("\n🧪 7. Testing normal C++ library with unit signal names...")
    compile_and_run_cpp(
        folder_name=f"{library_name}_units_cpp",
        exe_base_name="test_cpp_units"
    )

    # ---------------- EMBEDDED C TEST ----------------
    print("\n🧪 8. Testing embedded C library...")
    compile_and_run_c(
        folder_name=f"{library_name}_embedded",
        exe_base_name="test_c_embedded"
    )

    # ---------------- EMBEDDED C++ TEST ----------------
    print("\n🧪 9. Testing embedded C++ library...")
    compile_and_run_cpp(
        folder_name=f"{library_name}_embedded_cpp",
        exe_base_name="test_cpp_embedded"
    )

    # ---------------- CLEANUP ----------------
    print("\n🧹 10. Cleaning up temporary files...")
    delete_temp_files()

    print("\n✅ ALL NORMAL + EMBEDDED TESTS PASSED SUCCESSFULLY")
