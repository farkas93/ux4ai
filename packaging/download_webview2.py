"""Bundle a pinned, architecture-matched offline Microsoft WebView2 runtime."""

import hashlib
import json
import platform
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path


def download(root):
    if sys.platform != "win32":
        raise RuntimeError("The WebView2 CAB must be extracted on Windows")
    architecture = platform.machine().lower()
    architecture = "arm64" if architecture in {"arm64", "aarch64"} else "x86_64"
    manifest = json.loads((root / "packaging" / "webview2.json").read_text())
    expected = manifest[architecture]
    scratch = root / ".artifacts" / "webview2-download"
    scratch.mkdir(parents=True, exist_ok=True)
    archive = scratch / "runtime.cab"
    sha = hashlib.sha256()
    with urllib.request.urlopen(expected["url"]) as response, archive.open("wb") as file:
        for chunk in iter(lambda: response.read(1024 * 1024), b""):
            sha.update(chunk)
            file.write(chunk)
    if sha.hexdigest() != expected["sha256"]:
        raise RuntimeError("WebView2 archive checksum does not match the pinned runtime")
    extracted = scratch / "expanded"
    extracted.mkdir(exist_ok=True)
    subprocess.run(["expand.exe", "-F:*", str(archive), str(extracted)], check=True)
    executable = list(extracted.rglob("msedgewebview2.exe"))
    if len(executable) != 1:
        raise RuntimeError("The WebView2 archive did not contain one complete runtime")
    destination = root / ".artifacts" / "webview2"
    shutil.copytree(executable[0].parent, destination, dirs_exist_ok=True)
    return destination


if __name__ == "__main__":
    download(Path(__file__).resolve().parents[1])
