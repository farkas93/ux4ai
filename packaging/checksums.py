import hashlib
import json
from pathlib import Path


def write_checksums(directory, version, platform, architecture):
    name = f"AIProductToolkit-{version}-{platform}-{architecture}"
    files = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
             for path in directory.iterdir()
             if path.name.startswith(name) and not path.name.endswith("-checksums.json")}
    manifest = {"version": version, "platform": platform, "architecture": architecture, "files": files}
    (directory / (name + "-checksums.json")).write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    import platform
    import sys
    import tomllib

    root = Path(__file__).resolve().parents[1]
    version = tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"]
    arch = "arm64" if platform.machine().lower() in {"arm64", "aarch64"} else "x86_64"
    write_checksums(root / ".artifacts/releases", version, sys.platform, arch)
