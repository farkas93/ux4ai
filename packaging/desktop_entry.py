"""PyInstaller entry point; configure the local profile before backend imports."""

from aipm_toolkit.desktop import main

if __name__ == "__main__":
    raise SystemExit(main())
