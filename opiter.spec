# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Opiter (single-file Linux build).
#
# Usage:
#   uv run pyinstaller --noconfirm opiter.spec
#
# Output:
#   dist/opiter        — single executable
#
# To build for Windows / macOS, run the same spec on a native or VM
# host of that platform — PyInstaller does not cross-compile.

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# pdf2docx and PyMuPDF have hidden submodule imports.
hidden = (
    collect_submodules("pdf2docx")
    + collect_submodules("docx")
    + collect_submodules("hwp5")
    + collect_submodules("pymupdf")
)

# Data files shipped inside dependencies (e.g. pdf2docx fonts, pyhwp xsl).
datas = (
    collect_data_files("pdf2docx")
    + collect_data_files("docx")
    + collect_data_files("hwp5")
    + collect_data_files("pdfminer")
)


a = Analysis(
    ["src/opiter/main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "test", "unittest"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="opiter",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI app — no terminal
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# macOS-only: wrap the executable in a proper .app bundle. PyInstaller
# ignores the BUNDLE block on Linux and Windows so this is safe to keep.
app = BUNDLE(
    exe,
    name="Opiter.app",
    icon=None,
    bundle_identifier="dev.juhyeonl.opiter",
    info_plist={
        "CFBundleDisplayName": "Opiter",
        "CFBundleShortVersionString": "0.1.1",
        "NSHighResolutionCapable": True,
    },
)
