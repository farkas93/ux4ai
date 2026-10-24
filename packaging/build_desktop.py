"""Native desktop bundle and platform archives. Never cross-label emulated builds."""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tomllib
from pathlib import Path

from checksums import write_checksums
from icons import generate


def native_arch():
    value = platform.machine().lower()
    if value in {"amd64", "x86_64"}:
        return "x86_64"
    if value in {"arm64", "aarch64"}:
        return "arm64"
    raise RuntimeError(f"Unsupported native architecture: {value}")


def build():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-arch", choices=["x86_64", "arm64"], required=True)
    parser.add_argument("--bundle-only", action="store_true", help="Skip platform archive/installer creation")
    parser.add_argument("--archive-only", action="store_true", help="Archive an already built and qualified bundle")
    args = parser.parse_args()
    architecture = native_arch()
    if architecture != args.expected_arch:
        raise RuntimeError(f"Expected native {args.expected_arch} Python, found {architecture}")
    root = Path(__file__).resolve().parents[1]
    version = tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"]
    os.environ["AIPM_BUILD_VERSION"] = version
    output = root / ".artifacts" / "desktop-dist"
    bundle = output / "AIProductToolkit"
    if not args.archive_only:
        generate(root)
        if sys.platform == "win32":
            from download_webview2 import download

            download(root)
        subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
                        "--distpath", str(output), "--workpath", str(root / ".artifacts" / "pyinstaller-work"),
                        str(root / "packaging" / "desktop.spec")], cwd=root, check=True)
    else:
        from importlib.metadata import PathDistribution

        metadata = [*output.rglob("ai_product_toolkit-*.dist-info"),
                    *output.rglob("ai_product_toolkit.egg-info")]
        if not metadata or any(PathDistribution(path).version != version for path in metadata):
            raise RuntimeError("A bundle of the current application version must be built first")
    if args.bundle_only:
        return
    releases = root / ".artifacts" / "releases"
    releases.mkdir(parents=True, exist_ok=True)
    name = f"AIProductToolkit-{version}-{sys.platform}-{architecture}"
    if sys.platform == "win32":
        if os.getenv("AIPM_SIGN_WINDOWS") == "1":
            subprocess.run(["pwsh", "-File", str(root / "packaging/sign_windows.ps1"),
                            "-Target", str(bundle / "AIProductToolkit.exe")], check=True)
        shutil.make_archive(str(releases / name), "zip", output, bundle.name)
        compiler = os.getenv("AIPM_ISCC") or shutil.which("ISCC.exe") or shutil.which("iscc")
        if compiler is None:
            compiler = str(Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"))
                           / "Inno Setup 6" / "ISCC.exe")
        if not Path(compiler).exists():
            raise RuntimeError("Inno Setup is required to produce the Windows installer")
        subprocess.run([compiler, f"/DAppVersion={version}", f"/DBundleDir={bundle}",
                        f"/DReleaseDir={releases}", f"/DTargetArch={'arm64' if architecture == 'arm64' else 'x64compatible'}",
                        f"/DOutputName={name}-setup", str(root / "packaging" / "windows.iss")], check=True)
        if os.getenv("AIPM_SIGN_WINDOWS") == "1":
            subprocess.run(["pwsh", "-File", str(root / "packaging/sign_windows.ps1"),
                            "-Target", str(releases / (name + "-setup.exe"))], check=True)
    elif sys.platform == "darwin":
        subprocess.run(["hdiutil", "create", "-volname", "AI Product Toolkit", "-srcfolder",
                        str(output / "AIProductToolkit.app"), "-ov", "-format", "UDZO",
                        str(releases / (name + ".dmg"))], check=True)
    else:
        with tarfile.open(releases / (name + ".tar.gz"), "w:gz", compresslevel=3) as archive:
            archive.add(bundle, arcname=bundle.name)
    write_checksums(releases, version, sys.platform, architecture)


if __name__ == "__main__":
    build()
