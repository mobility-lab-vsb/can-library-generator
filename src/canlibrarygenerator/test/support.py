"""Shared DBC and native compilation fixtures."""
import os
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path

import cantools

from src.canlibrarygenerator.selection import DatabaseSelection
from src.canlibrarygenerator.generate_functions.generate_c_library import generate_c_code
from src.canlibrarygenerator.generate_functions.generate_cpp_library import generate_cpp_code


def database(signals, attributes="", name="Sample", frame=256, length=8):
    text = f'VERSION "test"\nNS_ :\nBS_:\nBU_: ECU\nBO_ {frame} {name}: {length} ECU\n{signals}\n{attributes}'
    db = cantools.database.load_string(text, database_format="dbc")
    db.name = "fixture.dbc"
    return db


def compile_and_run(test, db, body, language="c", embedded=False, hooks="", selected=None, **options):
    compiler = "gcc" if language == "c" else "g++"
    if not shutil.which(compiler):
        test.skipTest(f"{compiler} is required")
    tree = DatabaseSelection([db])
    if selected is not None:
        tree.selected_items = [sid for sid in tree.selected_items if tree.item(sid, "text") in selected]
    generate = generate_c_code if language == "c" else generate_cpp_code
    header, source = ("h", "c") if language == "c" else ("hpp", "cpp")
    outputs = generate(tree.selected_items, "test", [db], tree, message_modes=tree.message_modes,
                       embedded=embedded, **options)
    with tempfile.TemporaryDirectory(prefix="can_regression_") as temp:
        folder = Path(temp)
        names = [f"can_db_def.{header}", f"test_db.{header}", f"test_db.{source}",
                 f"test_interface.{header}", f"test_interface.{source}"]
        for name, text in zip(names, outputs):
            (folder / name).write_text(text, encoding="utf-8")
        main = folder / f"main.{source}"
        main.write_text(f'#include <assert.h>\n#include <string.h>\n#include "test_interface.{header}"\n'
                        'int sends = 0; int callbacks = 0;\n'
                        'void test_msg_send(const can_db_msg_t* msg) { (void)msg; ++sends; }\n'
                        'void callback(void) { ++callbacks; }\n' + hooks
                        + '\nint main(void) {\n' + body + '\nreturn 0; }\n', encoding="utf-8")
        executable = folder / ("test.exe" if os.name == "nt" else "test")
        flags = shlex.split(os.environ.get("CFLAGS" if language == "c" else "CXXFLAGS", ""))
        result = subprocess.run([compiler, "-std=c99" if language == "c" else "-std=c++11",
                                 "-Wall", "-Wextra", "-Werror", *flags, str(main),
                                 str(folder / names[2]), str(folder / names[4]), "-I", str(folder),
                                 "-o", str(executable), "-lm"], capture_output=True, text=True, timeout=60)
        test.assertEqual(result.returncode, 0, result.stderr)
        result = subprocess.run([str(executable)], capture_output=True, text=True, timeout=10)
        test.assertEqual(result.returncode, 0, result.stderr)
    return outputs
