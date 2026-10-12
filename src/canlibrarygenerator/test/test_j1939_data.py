"""Compile generated libraries and verify J1939 unused payload bits."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import cantools

from src.canlibrarygenerator.generate_functions.generate_c_library import generate_c_code
from src.canlibrarygenerator.generate_functions.generate_cpp_library import generate_cpp_code


class MockTree:
    def item(self, item, option):
        return ["Signal"] if option == "values" else item[1]

    def parent(self, item):
        return ("Message", item[0])


def make_database(formats, database_j1939=False):
    dbc = '\n'.join([
        'VERSION "test"', 'NS_ :', 'BS_:', 'BU_: ECU',
        *[
            f'BO_ {2147483937 + i} Msg{i}: 8 ECU\n'
            f' SG_ Value : 4|4@1+ (1,0) [0|15] "" ECU'
            for i in range(len(formats))
        ],
        'BA_DEF_ BO_ "VFrameFormat" ENUM "ExtendedCAN","J1939PG";',
        'BA_DEF_DEF_ "VFrameFormat" "ExtendedCAN";',
        *[
            f'BA_ "VFrameFormat" BO_ {2147483937 + i} {int(j1939)};'
            for i, j1939 in enumerate(formats)
        ],
        *([
            'BA_DEF_ "ProtocolType" STRING ;',
            'BA_ "ProtocolType" "J1939";',
        ] if database_j1939 else []),
    ])
    db = cantools.database.load_string(dbc, database_format="dbc")
    db.name = "test.dbc"
    return db


class J1939DataTests(unittest.TestCase):
    def test_initialization_and_packaging(self):
        for language, generate, compiler, extension in [
            ("c", generate_c_code, "gcc", "c"),
            ("cpp", generate_cpp_code, "g++", "cpp"),
        ]:
            if not shutil.which(compiler):
                self.skipTest(f"{compiler} is required")
            for formats, database_j1939 in [
                ([False], False), ([True], False),
                ([False], True), ([True, False], False),
            ]:
                for embedded in [False, True]:
                    with self.subTest(language=language, formats=formats,
                                      database_j1939=database_j1939, embedded=embedded):
                        db = make_database(formats, database_j1939)
                        selected = [(msg.name, "Value") for msg in db.messages]
                        outputs = generate(selected, "test", [db], MockTree(),
                                           embedded=embedded, generate_callback=False,
                                           generate_crc=False, generate_counter=False)
                        header_ext = "h" if language == "c" else "hpp"
                        names = [f"can_db_def.{header_ext}", f"test_db.{header_ext}",
                                 f"test_db.{extension}", f"test_interface.{header_ext}",
                                 f"test_interface.{extension}"]
                        checks = []
                        for i, j1939 in enumerate(formats):
                            fill = 255 if j1939 or database_j1939 else 0
                            expected = 0x2F if fill else 0x20
                            checks.append(f"""
    msg = test_find_message_by_id({289 + i});
    if (!msg) return 1;
    for (int b = 0; b < 64; ++b) {{
        if (msg->data[b] != {fill}) return 2;
    }}
    test_Msg{i}.Value->phys_value = 2;
    if (test_package_message(msg->id) != 0) return 3;
    if (msg->data[0] != {expected}) return 4;
    for (int b = 1; b < msg->length; ++b) {{
        if (msg->data[b] != {fill}) return 5;
    }}
    /* Repack after dirtying the buffer to verify memset runs every time. */
    for (int b = 0; b < msg->length; ++b) msg->data[b] = 0xAA;
    if (test_package_message(msg->id) != 0) return 6;
    if (msg->data[0] != {expected}) return 7;
    for (int b = 1; b < msg->length; ++b) {{
        if (msg->data[b] != {fill}) return 8;
    }}
""")
                        with tempfile.TemporaryDirectory(prefix="can_j1939_") as temp:
                            folder = Path(temp)
                            for name, content in zip(names, outputs):
                                (folder / name).write_text(content, encoding="utf-8")
                            main = folder / f"main.{extension}"
                            main.write_text(
                                f'#include "test_interface.{header_ext}"\n'
                                'int main(void) {\n    can_db_msg_t *msg;\n'
                                + ''.join(checks) + '    return 0;\n}\n', encoding="utf-8")
                            executable = folder / "test.exe"
                            result = subprocess.run([
                                compiler, "-std=c99" if language == "c" else "-std=c++17",
                                str(main), str(folder / names[2]), str(folder / names[4]),
                                "-I", str(folder), "-o", str(executable), "-lm",
                            ], capture_output=True, text=True)
                            self.assertEqual(result.returncode, 0, result.stderr)
                            result = subprocess.run([str(executable)], capture_output=True, text=True)
                            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
