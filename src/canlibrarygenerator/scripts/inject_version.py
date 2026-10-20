"""Set runtime and native packaging versions from one validated version string."""
import argparse
import re
from pathlib import Path

import toml
from packaging.version import Version


def inject_version(raw_version, root=None):
    root = Path(root) if root else Path(__file__).resolve().parents[3]
    version = Version(raw_version.removeprefix("v"))
    runtime = root / "src" / "canlibrarygenerator" / "__init__.py"
    text = runtime.read_text(encoding="utf-8")
    text, count = re.subn(r'^__version__ = .*$', f'__version__ = "{version}"', text, flags=re.M)
    if count != 1:
        raise ValueError("Expected exactly one runtime version declaration")
    config_file = root / "pyproject.toml"
    config = toml.loads(config_file.read_text(encoding="utf-8"))
    native = ".".join(str(part) for part in (version.release + (0, 0, 0))[:3])
    config["tool"]["briefcase"]["version"] = native
    runtime.write_text(text, encoding="utf-8")
    config_file.write_text(toml.dumps(config), encoding="utf-8")
    print(f"Runtime version: {version}; native package version: {native}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version")
    args = parser.parse_args()
    inject_version(args.version)


if __name__ == "__main__":
    main()
