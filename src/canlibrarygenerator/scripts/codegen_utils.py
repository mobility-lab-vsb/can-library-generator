"""Headless generation of C and C++ libraries from any supported DBC."""
from pathlib import Path

from ..selection import DatabaseSelection
from ..service import load_database


def generate_all_code(dbc_filename, library_name, generate_c_code, generate_cpp_code,
                      embedded=False, output_suffix="", with_units=False,
                      generate_counter=True, generate_crc=True, generate_callback=True,
                      output_dir=None):
    db = load_database(dbc_filename)
    tree = DatabaseSelection([db])
    output = Path(output_dir) if output_dir is not None else Path(__file__).resolve().parents[1] / "temp"
    options = dict(message_modes=tree.message_modes, embedded=embedded, with_units=with_units,
                   generate_counter=generate_counter, generate_crc=generate_crc,
                   generate_callback=generate_callback)
    for generate, suffix, header, source in (
        (generate_c_code, "", "h", "c"),
        (generate_cpp_code, "_cpp", "hpp", "cpp"),
    ):
        contents = generate(tree.selected_items, library_name, [db], tree, **options)
        folder = output / f"{library_name}{output_suffix}{suffix}"
        folder.mkdir(parents=True, exist_ok=True)
        names = [f"can_db_def.{header}", f"{library_name}_db.{header}",
                 f"{library_name}_db.{source}", f"{library_name}_interface.{header}",
                 f"{library_name}_interface.{source}"]
        for name, text in zip(names, contents):
            (folder / name).write_text(text, encoding="utf-8")
