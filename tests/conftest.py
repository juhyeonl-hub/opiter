"""pytest configuration: force Qt to use the offscreen platform during tests.

Must be imported before any PySide6 modules. pytest loads conftest.py before
collecting test modules, so this is the right place.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
