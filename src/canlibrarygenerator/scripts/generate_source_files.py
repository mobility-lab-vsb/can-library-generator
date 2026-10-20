"""Generate both API variants for Doxygen without GUI dependencies."""
import argparse
from pathlib import Path

from ..generate_functions.generate_c_library import generate_c_code
from ..generate_functions.generate_cpp_library import generate_cpp_code
from .codegen_utils import generate_all_code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=".docs-build/input")
    args = parser.parse_args()
    dbc = Path(__file__).resolve().parents[1] / "dbc" / "CAN_example.dbc"
    generate_all_code(dbc, "cangen", generate_c_code, generate_cpp_code, output_dir=args.output)


if __name__ == "__main__":
    main()
