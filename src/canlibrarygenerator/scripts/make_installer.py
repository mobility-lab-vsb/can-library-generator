"""Render one shared Windows installer definition for dev and release builds."""
from pathlib import Path

import toml


def render_installer(root=None):
    root = Path(root) if root else Path(__file__).resolve().parents[3]
    config = toml.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    version = config["tool"]["briefcase"]["version"]
    app = config["tool"]["briefcase"]["app"]["canlibrarygenerator"]
    executable = app["app_name"] if app.get("console_app", False) else app["formal_name"]
    source = root / "installer.iss.in"
    text = source.read_text(encoding="utf-8").replace("@VERSION@", version)
    return text.replace("@APP_EXECUTABLE@", f"{executable}.exe")


def main():
    root = Path(__file__).resolve().parents[3]
    (root / "installer.iss").write_text(render_installer(root), encoding="utf-8")


if __name__ == "__main__":
    main()
