# -*- mode: python ; coding: utf-8 -*-

import sys

# Define platform-specific dependencies
hidden_imports = ['parser', 'appdirs', 'pkg_resources']
if sys.platform == 'linux':
    hidden_imports.append('gi')
elif sys.platform == 'win32':
    hidden_imports.append('clr')

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[('frontend', 'frontend')],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pandas', 'numpy', 'matplotlib', 'PyQt5', 'PyQtWebEngine', 'PySide2', 'PySide6', 'tkinter', 'unittest', 'pydoc'],
    noarchive=False,
    optimize=2,
)

# Optimization: Filter out heavy GTK assets (icons, themes, etc.)
# We keep only the essential binaries and the frontend data.
# This significantly reduces the size of the 'onefile' bundle.
def filter_datas(datas):
    return [d for d in datas if 'share' not in d[0].lower() or 'frontend' in d[0].lower()]

a.datas = filter_datas(a.datas)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='MPesaAnalytics',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True, # Strip symbols to save space
    upx=False,  # UPX not available
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False, # No console for the final user
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
