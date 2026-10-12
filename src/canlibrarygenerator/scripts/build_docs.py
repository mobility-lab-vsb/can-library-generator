"""Generate reference documentation from current C/C++ templates."""
import shutil
import subprocess
from pathlib import Path

from ..generate_functions.generate_c_library import generate_c_code
from ..generate_functions.generate_cpp_library import generate_cpp_code
from .codegen_utils import generate_all_code


def main():
    root = Path(__file__).resolve().parents[3]
    input_dir = root / ".docs-build" / "input"
    api_dir = root / "docs" / "api"
    for target in (input_dir, api_dir):
        if target.is_symlink() or not target.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"Unsafe documentation output: {target}")
        if target.exists():
            shutil.rmtree(target)
    generate_all_code(root / "src/canlibrarygenerator/dbc/CAN_example.dbc", "cangen",
                      generate_c_code, generate_cpp_code, output_dir=input_dir)
    config = (root / "Doxyfile").read_text(encoding="utf-8")
    for language, folder in (("c", "cangen"), ("cpp", "cangen_cpp")):
        (api_dir / language).mkdir(parents=True, exist_ok=True)
        language_config = (config + f'\nINPUT = docs/guide.md .docs-build/input/{folder}\n'
                           + f'HTML_OUTPUT = api/{language}\n')
        subprocess.run(["doxygen", "-"], input=language_config, encoding="utf-8",
                       cwd=root, check=True)
        if not (api_dir / language / "index.html").is_file():
            raise RuntimeError(f"Doxygen did not produce the {language} HTML index")
    (api_dir / "index.html").write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<title>CAN Library Generator API</title></head><body>'
        '<h1>CAN Library Generator API</h1><p><a href="c/index.html">C reference</a></p>'
        '<p><a href="cpp/index.html">C++ reference</a></p></body></html>\n', encoding="utf-8")
    # Normalize Doxygen's bundled HTML/CSS/JS for reviewable repository diffs.
    for path in api_dir.rglob("*"):
        if path.suffix in (".html", ".css", ".js"):
            text = path.read_text(encoding="utf-8")
            text = "\n".join(line.rstrip() for line in text.splitlines()).rstrip() + "\n"
            path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
