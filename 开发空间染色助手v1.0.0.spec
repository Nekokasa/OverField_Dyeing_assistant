# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ['keyboard', 'win32api', 'PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets', 'PyQt5.sip', 'win32gui', 'win32event', 'win32api', 'winerror', 'win32con', 'color_card_util', 'ui_logic_mini', 'logger_util']
hiddenimports += collect_submodules('PyQt5')


a = Analysis(
    ['d:\\Desktop\\python\\OverField_Dyeing_assistant\\rsc\\color_matcher_mini.py'],
    pathex=[],
    binaries=[],
    datas=[('d:\\Desktop\\python\\OverField_Dyeing_assistant\\config', 'config'), ('d:\\Desktop\\python\\OverField_Dyeing_assistant\\rsc', 'rsc'), ('d:\\Desktop\\python\\OverField_Dyeing_assistant\\icon', 'icon'), ('d:\\Desktop\\python\\OverField_Dyeing_assistant\\log', 'log')],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [('v', None, 'OPTION')],
    exclude_binaries=True,
    name='开发空间染色助手v1.0.0',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['d:\\Desktop\\python\\OverField_Dyeing_assistant\\icon\\icon.png'],
    manifest='d:\\Desktop\\python\\OverField_Dyeing_assistant\\app.manifest',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='开发空间染色助手v1.0.0',
)
