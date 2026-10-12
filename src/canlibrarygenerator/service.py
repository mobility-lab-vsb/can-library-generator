"""DBC loading and library export, independent of Qt."""
from pathlib import Path

import cantools

from .ir.builder import validate_identifier


def load_database(path):
    path = Path(path)
    db = cantools.database.load_file(path)
    db.name = path.name
    return db


def export_library(contents, library_name, directory, language="c", include_definitions=True):
    validate_identifier(library_name, "Library prefix")
    if language not in ("c", "cpp"):
        raise ValueError("Language must be 'c' or 'cpp'")
    header, source = ("h", "c") if language == "c" else ("hpp", "cpp")
    def_h, db_h, db_c, int_h, int_c = contents
    output = Path(directory) / library_name
    files = {
        output / "inc" / f"{library_name}_db.{header}": db_h,
        output / "src" / f"{library_name}_db.{source}": db_c,
        output / "inc" / f"{library_name}_interface.{header}": int_h,
        output / "src" / f"{library_name}_interface.{source}": int_c,
    }
    if include_definitions:
        files[output / "inc" / f"can_db_def.{header}"] = def_h
    for path, text in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return list(files)
