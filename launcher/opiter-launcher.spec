# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the Opiter Launcher (small bootstrap installer).
#
# Goal: keep the .exe / .dmg / binary as small as possible. The launcher
# only needs QtCore + QtGui + QtWidgets + QtNetwork. Everything PyMuPDF /
# pdf2docx / mammoth / pyhwp is excluded — those land in the main
# Opiter binary, which the launcher downloads at runtime.

import sys

IS_MAC = sys.platform == "darwin"

# Aggressive Qt module exclusions — keep the launcher binary lean.
qt_excludes = [
    "PySide6.Qt3DAnimation",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DExtras",
    "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic",
    "PySide6.Qt3DRender",
    "PySide6.QtBluetooth",
    "PySide6.QtCharts",
    "PySide6.QtConcurrent",
    "PySide6.QtDataVisualization",
    "PySide6.QtDBus",
    "PySide6.QtDesigner",
    "PySide6.QtHelp",
    "PySide6.QtLocation",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtNfc",
    "PySide6.QtOpenGL",
    "PySide6.QtOpenGLFunctions",
    "PySide6.QtOpenGLWidgets",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.QtPositioning",
    "PySide6.QtPrintSupport",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuick3D",
    "PySide6.QtQuickControls2",
    "PySide6.QtQuickWidgets",
    "PySide6.QtRemoteObjects",
    "PySide6.QtScxml",
    "PySide6.QtSensors",
    "PySide6.QtSerialBus",
    "PySide6.QtSerialPort",
    "PySide6.QtSpatialAudio",
    "PySide6.QtSql",
    "PySide6.QtStateMachine",
    "PySide6.QtSvg",
    "PySide6.QtSvgWidgets",
    "PySide6.QtTest",
    "PySide6.QtTextToSpeech",
    "PySide6.QtUiTools",
    "PySide6.QtWebChannel",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebSockets",
    "PySide6.QtWebView",
    "PySide6.QtXml",
]

heavy_excludes = [
    "fitz", "pymupdf", "pypdf", "pdfplumber", "pdfminer", "pdf2docx",
    "docx", "mammoth", "hwp5", "PIL", "numpy", "pytest", "pytest_qt",
    "tkinter",
]

a = Analysis(
    ["launch.py"],
    pathex=["."],  # so ``opiter_launcher`` is importable as a package
    binaries=[],
    datas=[],
    hiddenimports=[
        "opiter_launcher",
        "opiter_launcher.main",
        "opiter_launcher.wizard",
        "opiter_launcher.github",
        "opiter_launcher.downloader",
        "opiter_launcher.paths",
        # We use Qt's networking (QNetworkAccessManager) so we don't
        # have to bundle Python's OpenSSL — that bundle was the
        # SmartScreen / Smart App Control trigger that blocked v0.1.13.
        "PySide6.QtNetwork",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=qt_excludes + heavy_excludes,
    noarchive=False,
)

pyz = PYZ(a.pure)

if IS_MAC:
    exe = EXE(
        pyz, a.scripts, [],
        exclude_binaries=True,
        name="opiter-setup",
        debug=False, strip=False, upx=False,
        console=False, argv_emulation=False,
    )
    coll = COLLECT(
        exe, a.binaries, a.datas,
        strip=False, upx=False, name="opiter-setup",
    )
    app = BUNDLE(
        coll,
        name="Opiter Setup.app",
        icon=None,
        bundle_identifier="dev.juhyeonl.opiter.setup",
        info_plist={"CFBundleShortVersionString": "0.1.0"},
    )
else:
    exe = EXE(
        pyz, a.scripts, a.binaries, a.datas, [],
        name="opiter-setup",
        debug=False,
        strip=False,
        upx=False,
        runtime_tmpdir=None,
        console=False,
    )
