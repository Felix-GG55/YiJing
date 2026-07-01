# -*- mode: python ; coding: utf-8 -*-
"""
YiJing onedir spec (PyInstaller 6.x)
- EXE uses exclude_binaries=True so bootloader is pure (no PKG appended)
- COLLECT writes exe + _internal/ (binaries + datas + PYZ + pure .pyc)
- User runs dist/YiJing/YiJing.exe with _internal/ next to it
"""
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []

# 自带典籍清单(JSON,131 本),运行时随 EXE 发布
datas += [('yi_books_manifest.json', '.')]

# v4.1 资源
ICON_ICO = 'assets/icon.ico'
ICON_PNG = 'assets/icon.png'
MANTRA_WAV = 'assets/sounds/mantra.wav'

if os.path.exists(ICON_PNG):
    datas += [(ICON_PNG, '.')]
if os.path.exists(MANTRA_WAV):
    datas += [(MANTRA_WAV, 'sounds')]

tmp_ret = collect_all('tkinter')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]


a = Analysis(
    ['yi_gui.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
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
    [],
    [],
    exclude_binaries=True,
    name='YiJing',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON_ICO if os.path.exists(ICON_ICO) else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='YiJing',
)
