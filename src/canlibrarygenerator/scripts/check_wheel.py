"""Smoke-test packaged imports, templates and GUI resources away from the source tree."""
import argparse
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


SMOKE_TEST = '''
from pathlib import Path
import cantools
import canlibrarygenerator
from canlibrarygenerator.selection import DatabaseSelection
from canlibrarygenerator.generate_functions.generate_c_library import generate_c_code
from canlibrarygenerator.generate_functions.generate_cpp_library import generate_cpp_code
from canlibrarygenerator.ui.window import DBCLibraryGenerator
from PyQt6.QtWidgets import QApplication

root = Path(canlibrarygenerator.__file__).parent
assert root.parent == Path.cwd(), root
db = cantools.database.load_file(root / "dbc/CAN_example.dbc")
db.name = "CAN_example.dbc"
tree = DatabaseSelection([db])
for generate in (generate_c_code, generate_cpp_code):
    result = generate(tree.selected_items, "smoke", [db], tree,
                      message_modes=tree.message_modes, embedded=True)
    assert len(result) == 5 and all(result)
    assert "smoke_package_message_raw" in result[4]
app = QApplication([])
window = DBCLibraryGenerator()
assert not window.windowIcon().isNull()
assert not window.logo_label.pixmap().isNull()
window.close()
print("Wheel imports, C/C++ templates, icon and logo: OK")
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", nargs="?")
    args = parser.parse_args()
    wheels = [Path(args.wheel)] if args.wheel else sorted(Path("dist").glob("*.whl"),
                                                        key=lambda p: p.stat().st_mtime)
    if not wheels:
        parser.error("Build a wheel first")
    with tempfile.TemporaryDirectory(prefix="can_wheel_") as temp:
        with zipfile.ZipFile(wheels[-1]) as archive:
            if any("/test/" in name for name in archive.namelist()):
                raise ValueError("Tests must not be included in the application wheel")
            archive.extractall(temp)
        env = dict(os.environ, PYTHONPATH=temp, QT_QPA_PLATFORM="offscreen")
        subprocess.run([sys.executable, "-c", SMOKE_TEST], cwd=temp, env=env, check=True,
                       timeout=60)


if __name__ == "__main__":
    main()
