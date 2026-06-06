# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the Bazar Market Print Agent desktop app (GUI).
# Build: pyinstaller gui.spec
#
# Produces a windowed (no-console) single-file exe so non-technical shop staff
# just double-click it and get a real app window. agent.py is pulled in
# automatically because gui.py imports it.

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

escpos_datas = collect_data_files('escpos')  # capabilities.json, templates/, etc.
escpos_hidden = collect_submodules('escpos')

# CustomTkinter ships theme .json files and assets it loads at runtime — without
# these the windowed exe crashes on launch with a "theme not found" error.
ctk_datas = collect_data_files('customtkinter')

a = Analysis(
    ['gui.py'],
    pathex=[],
    binaries=[],
    datas=escpos_datas + ctk_datas,
    hiddenimports=[
        'usb',
        'usb.core',
        'usb.util',
        'usb.backend',
        'usb.backend.libusb1',
        'usb.backend.libusb0',
        'usb.backend.openusb',
        'win32print',
        'customtkinter',
        'darkdetect',
        'PIL',
        'PIL._tkinter_finder',
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
    console=False,           # windowed app — no terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    icon=None,
)
