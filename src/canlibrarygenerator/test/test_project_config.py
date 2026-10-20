"""Check release version consistency and required CI dependencies."""
import shutil
import tempfile
import tomllib
import unittest
from pathlib import Path

import yaml

from src.canlibrarygenerator.scripts.inject_version import inject_version
from src.canlibrarygenerator.scripts.make_installer import render_installer


ROOT = Path(__file__).resolve().parents[3]


class ProjectConfigTests(unittest.TestCase):
    def test_installer_uses_briefcase_gui_executable(self):
        text = render_installer(ROOT)
        self.assertIn('Filename: "{app}\\CANLibraryGenerator.exe"', text)
        self.assertIn('UninstallDisplayIcon={app}\\CANLibraryGenerator.exe', text)
        self.assertNotIn('@APP_EXECUTABLE@', text)
        self.assertNotIn('@VERSION@', text)

    def test_runtime_and_native_dependencies_match(self):
        config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(config["project"]["dependencies"],
                         config["tool"]["briefcase"]["app"]["canlibrarygenerator"]["requires"])

    def test_linux_package_uses_distribution_python(self):
        workflow = yaml.load((ROOT / ".github/workflows/build.yml").read_text(encoding="utf-8"),
                             Loader=yaml.BaseLoader)
        job = workflow["jobs"]["package"]
        linux = next(platform for platform in job["strategy"]["matrix"]["include"]
                     if platform["platform"] == "linux")
        # Ubuntu's system-package backend rejects a different Python minor version.
        self.assertEqual((linux["os"], linux["python"]), ("ubuntu-24.04", "3.12"))
        setup = next(step for step in job["steps"] if step.get("uses") == "actions/setup-python@v5")
        self.assertEqual(setup["with"]["python-version"], "${{ matrix.python }}")

    def test_version_injection_and_invalid_version(self):
        with tempfile.TemporaryDirectory(prefix="can_version_") as temp:
            root = Path(temp)
            runtime = root / "src/canlibrarygenerator/__init__.py"
            runtime.parent.mkdir(parents=True)
            runtime.write_text('__version__ = "0.0.0.dev0"\n', encoding="utf-8")
            shutil.copyfile(ROOT / "pyproject.toml", root / "pyproject.toml")
            for version, numeric in (("v4.8.1", "4.8.1"), ("0.0.0.dev42", "0.0.0")):
                inject_version(version, root)
                self.assertIn(version.removeprefix("v"), runtime.read_text(encoding="utf-8"))
                config = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
                self.assertEqual(config["tool"]["briefcase"]["version"], numeric)
            before = runtime.read_bytes(), (root / "pyproject.toml").read_bytes()
            with self.assertRaises(ValueError):
                inject_version("invalid version", root)
            self.assertEqual(before, (runtime.read_bytes(), (root / "pyproject.toml").read_bytes()))

    def test_releases_wait_for_checks_and_all_platforms(self):
        def workflow(name):
            return yaml.load((ROOT / ".github/workflows" / name).read_text(encoding="utf-8"),
                             Loader=yaml.BaseLoader)
        tests = workflow("test.yml")
        self.assertEqual(tests["on"]["push"]["branches"], ["**"])
        self.assertIn("pull_request", tests["on"])
        self.assertEqual(set(tests["jobs"]["test"]["strategy"]["matrix"]["os"]),
                         {"ubuntu-22.04", "windows-latest", "macos-latest"})
        for name in ("release.yml", "dev_build.yml"):
            jobs = workflow(name)["jobs"]
            self.assertIn("checks", jobs["build"]["needs"])
        release = workflow("release.yml")["jobs"]
        self.assertIn("build", release["publish"]["needs"])
        platforms = workflow("build.yml")["jobs"]["package"]["strategy"]["matrix"]["include"]
        self.assertEqual({platform["extension"] for platform in platforms}, {"exe", "dmg", "deb"})
