# Native builds run with the desktop + packaging extras, without server extras.
import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, copy_metadata

root = Path(SPECPATH).parent
windows = sys.platform == "win32"
mac = sys.platform == "darwin"
assets = root / "aipm_toolkit" / "assets"
datas = []
for dependency in ("gradio", "gradio_client", "safehttpx", "groovy"):
    datas += collect_data_files(dependency)
datas += collect_data_files("aipm_toolkit", includes=["locales/**", "assets/**"])
for package in ("ai-product-toolkit", "gradio", "gradio_client", "huggingface_hub", "safehttpx"):
    datas += copy_metadata(package)
for source_name in ("alembic", "baseline"):
    for file in (root / source_name).rglob("*"):
        if file.is_file() and "__pycache__" not in file.parts:
            relative = file.relative_to(root / source_name)
            datas.append((str(file), str(Path("aipm_toolkit/assets") / source_name / relative.parent)))
datas.append((str(root / "alembic.ini"), "aipm_toolkit/assets"))
hidden = ["uvicorn.loops.asyncio", "uvicorn.protocols.http.h11_impl", "uvicorn.lifespan.on",
          "sqlalchemy.dialects.sqlite.pysqlite", "PySide6.QtCore", "PySide6.QtGui",
          "PySide6.QtWidgets", "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtSvg"]
excludes = ["psycopg", "psycopg_binary", "psycopg_pool", "PyQt5", "PyQt6", "tkinter",
            "pytest", "_pytest", "coverage"]
if windows:
    fixed = root / ".artifacts" / "webview2"
    if not (fixed / "msedgewebview2.exe").exists():
        raise RuntimeError("Run packaging/download_webview2.py before a Windows build")
    datas.append((str(fixed), "aipm_toolkit/assets/webview2"))
    hidden.append("PySide6.QtWebView")
    excludes += ["PySide6.QtWebEngineCore", "PySide6.QtWebEngineQuick", "PySide6.QtWebEngineWidgets"]
else:
    hidden += ["PySide6.QtWebEngineCore", "PySide6.QtWebEngineQuick"]
    excludes.append("PySide6.QtWebView")

a = Analysis(
    [str(root / "packaging" / "desktop_entry.py")], pathex=[str(root)],
    binaries=[], datas=datas, hiddenimports=hidden, excludes=excludes,
    runtime_hooks=[str(root / "packaging" / "runtime_gradio.py")],
    module_collection_mode={"gradio": "pyz+py"},
)
pyz = PYZ(a.pure)
icon = root / ".artifacts" / "icons" / ("icon.icns" if mac else "icon.ico")
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name="AIProductToolkit",
    debug=False, strip=False, upx=False, console=not (windows or mac),
    icon=str(icon) if windows or mac else None,
    codesign_identity=os.getenv("MACOS_SIGNING_IDENTITY") if mac else None,
    entitlements_file=str(root / "packaging" / "macos-entitlements.plist") if mac else None,
)
collection = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="AIProductToolkit")
if mac:
    app = BUNDLE(
        collection, name="AIProductToolkit.app", icon=str(icon),
        bundle_identifier="org.aiproducttoolkit.desktop",
        info_plist={"CFBundleShortVersionString": os.environ["AIPM_BUILD_VERSION"],
                    "CFBundleVersion": os.environ["AIPM_BUILD_VERSION"],
                    "LSMinimumSystemVersion": "14.0", "NSHighResolutionCapable": True},
    )
