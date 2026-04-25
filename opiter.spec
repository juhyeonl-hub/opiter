# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Opiter.
#
# Linux / Windows: single-file ("onefile") executable — distributed as
# a .deb (Linux) or bare .exe (Windows).
# macOS: "onedir" mode wrapped in a proper .app bundle. Apple's security
# does not play well with PyInstaller's onefile mode wrapped in a .app,
# and onefile + onedir distribution is the official PyInstaller
# recommendation for macOS.

import sys

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

IS_MAC = sys.platform == "darwin"

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


if IS_MAC:
    # onedir: EXE wraps just the launcher; binaries + datas are loose
    # files in the COLLECT folder, which BUNDLE then packages into .app.
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="opiter",
        debug=False,
        strip=False,
        upx=False,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name="opiter",
    )
    app = BUNDLE(
        coll,
        name="Opiter.app",
        icon=None,
        bundle_identifier="dev.juhyeonl.opiter",
        info_plist={
            "CFBundleDisplayName": "Opiter",
            "CFBundleShortVersionString": "0.1.13",
            "NSHighResolutionCapable": True,
        },
    )
else:
    # onefile: single self-extracting executable.
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
        upx=False,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
