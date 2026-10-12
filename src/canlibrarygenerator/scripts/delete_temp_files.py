"""Remove only the generator's dedicated legacy temp directory."""
import shutil
from pathlib import Path


def delete_temp_files():
    root = Path(__file__).resolve().parents[1]
    target = root / "temp"
    if target.is_symlink():
        raise ValueError("Refusing to follow a symlink while cleaning generated files")
    if target.exists():
        shutil.rmtree(target)


if __name__ == "__main__":
    delete_temp_files()
