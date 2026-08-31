# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('.env', '.'), ('icon.ico', '.'), ('icon.png', '.'), ('icon_check.png', '.'), ('icon_chevron.png', '.')]
binaries = []
hiddenimports = [
    'pynput.keyboard._win32',
    'pynput.mouse._win32',
    'ctypes',
    'ctypes.wintypes',
    'sounddevice',
    'soundfile',
    'pyperclip',
    'huggingface_hub',
]

for pkg in ['llama_cpp', 'ctranslate2', 'faster_whisper']:
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    ['diktat.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PyQt5', 'matplotlib', 'tkinter', 'pygame', 'pandas', 'jinja2',
        'lxml', 'xmlrpc', 'unittest', 'IPython', 'notebook', 'sympy',
        'zmq', 'tornado', 'sqlite3', 'test', 'distutils', 'pydoc'
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Diktat',
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
    icon=['icon.ico'],
)
