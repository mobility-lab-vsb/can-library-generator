import sys
import toml
import re

raw_version = sys.argv[1]

# Remove 'v' prefix and optional suffix like "-Test"
version = re.sub(r"^v", "", raw_version)
version = version.split("-")[0]

print(f"Injecting version: {version}")

with open("pyproject.toml", "r", encoding="utf-8") as f:
    data = toml.load(f)

data["project"]["version"] = version
data["tool"]["briefcase"]["version"] = version

with open("pyproject.toml", "w", encoding="utf-8") as f:
    toml.dump(data, f)