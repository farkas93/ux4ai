"""Qualify the real frozen executable and window, not the build environment."""

import argparse
import json
import os
import platform
import struct
import subprocess
import sys
from pathlib import Path


def binary_architecture(path):
    with path.open("rb") as file:
        header = file.read(64)
        if header.startswith(b"MZ"):
            file.seek(struct.unpack_from("<I", header, 60)[0] + 4)
            return {0x8664: "x86_64", 0xAA64: "arm64"}.get(struct.unpack("<H", file.read(2))[0])
        if header.startswith(b"\x7fELF"):
            return {62: "x86_64", 183: "arm64"}.get(struct.unpack_from("<H", header, 18)[0])
        magic = struct.unpack_from("<I", header)[0]
        if magic in {0xFEEDFACF, 0xFEEDFACE}:
            return {0x01000007: "x86_64", 0x0100000C: "arm64"}.get(struct.unpack_from("<I", header, 4)[0])
    raise ValueError("Unrecognized or universal executable; qualify an explicit native target")


def executable(root):
    if sys.platform == "win32":
        return root / "AIProductToolkit/AIProductToolkit.exe"
    if sys.platform == "darwin":
        return root / "AIProductToolkit.app/Contents/MacOS/AIProductToolkit"
    return root / "AIProductToolkit/AIProductToolkit"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle-root", type=Path, default=Path(".artifacts/desktop-dist"))
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--expected-arch", choices=["x86_64", "arm64"], required=True)
    args = parser.parse_args()
    program = executable(args.bundle_root.resolve())
    assert binary_architecture(program) == args.expected_arch
    subprocess.run([str(program), "--smoke-test", "--data-dir", str(args.profile.resolve())],
                    check=True, timeout=90, cwd=args.profile.parent)
    result = json.loads((args.profile / "native-smoke.json").read_text())
    assert result["ready"] is True
    assert result["sections"] == 6 and result["graphs"] is True
    assert not (args.profile / "instance.json").exists()
    # The full HTTP roundtrip tests now run against this frozen executable.
    environment = os.environ.copy()
    environment["AIPM_TEST_EXECUTABLE"] = str(program)
    subprocess.run([sys.executable, "-m", "pytest", "tests/test_desktop_process.py", "-q"],
                    env=environment, check=True, timeout=120)
    print(f"Qualified {sys.platform} {platform.machine()} frozen runtime and native window")


if __name__ == "__main__":
    main()
