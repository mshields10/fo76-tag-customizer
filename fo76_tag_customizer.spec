# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for FO76 Tag Customizer
#
# Build with:
#   pyinstaller fo76_tag_customizer.spec
# or use the helper:
#   .\build.ps1

import os

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=[
        os.path.join(SPECPATH, 'scripts'),
        os.path.join(SPECPATH, 'gui'),
    ],
    binaries=[],
    datas=[
        ('data/tidy_wasteland_analysis.json', 'data'),
    ],
    hiddenimports=[
        'parser',
        'diff',
        'compiler',
        'tagger',
        'extract_ba2',
        'gui.main_window',
        'gui.settings_dialog',
        'gui.utils',
        'gui.widgets.search_bar',
        'gui.widgets.tag_editor',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='FO76TagCustomizer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,       # no terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,           # add an .ico here when you have one
)
