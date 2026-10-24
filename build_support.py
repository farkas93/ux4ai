"""Collect the same immutable resources for wheels and frozen desktop bundles."""

import shutil
from pathlib import Path

from setuptools.command.build_py import build_py


class BuildPy(build_py):
    def run(self):
        super().run()
        root = Path(__file__).parent
        assets = Path(self.build_lib) / "aipm_toolkit" / "assets"
        assets.mkdir(parents=True, exist_ok=True)
        for name in ("alembic", "baseline"):
            shutil.copytree(root / name, assets / name, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copyfile(root / "alembic.ini", assets / "alembic.ini")
