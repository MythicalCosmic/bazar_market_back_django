# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Bazar Market Print Agent
# Build: pyinstaller agent.spec

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

escpos_datas = collect_data_files('escpos')  # capabilities.json, templates/, etc.
escpos_hidden = collect_submodules('escpos')

a = Analysis(
    ['agent.py'],
    pathex=[],
    binaries=[],
    datas=escpos_datas,
    hiddenimports=[
        'usb',
        'usb.core',
        'usb.util',
        'usb.backend',
        'usb.backend.libusb1',
        'usb.backend.libusb0',
        'usb.backend.openusb',
        'win32print',
    ] + escpos_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='BazarMarketPrinter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    icon=None,
)
