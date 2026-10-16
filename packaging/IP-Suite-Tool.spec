# -*- mode: python ; coding: utf-8 -*-
"""Shared static-resource whitelist for release and development builds."""
import os
from pathlib import Path

PROJECT_ROOT = Path(SPECPATH).resolve().parent
SOURCE = PROJECT_ROOT / 'src'
MODE = os.environ.get('IP_SUITE_BUILD_MODE', 'release')
if MODE not in {'release', 'development'}:
    raise ValueError('Unknown build mode')
DEVELOPMENT = MODE == 'development'
NAME = 'IP-Suite-Tool-dev' if DEVELOPMENT else 'IP-Suite-Tool'
DATAS = [
    (str(SOURCE / 'cfgs/cfg_mapping_config.json'), 'cfgs'),
    (str(SOURCE / 'defaults/cfg_ipv6_instance_prefix.json'), 'defaults'),
    (str(SOURCE / 'ico/ico.png'), 'ico'),
]
# Optional packages in a developer's environment are not application dependencies.
EXCLUDES = [
    'unittest', 'pytest', 'pdb', 'test', 'doctest', 'cProfile', 'profile', 'trace',
    'venv', 'ensurepip', 'turtle', 'tkinter.turtle', 'curses', 'antigravity',
    'docxcompose', 'docxtpl', 'pygame', 'torch', 'tensorflow', 'scipy',
    'matplotlib', 'torchvision', 'nltk', 'numba', 'sklearn', 'pyarrow',
    'sqlalchemy', 'aiohttp', 'paramiko', 'zstandard', 'PySide6', 'PySide2',
    'PyQt6', 'PyQt5', 'IPython', 'jupyter', 'notebook', 'sentry_sdk',
]
a = Analysis(
    [str(SOURCE / 'main.py')],
    pathex=[str(SOURCE)], binaries=[], datas=DATAS,
    hiddenimports=['ipaddress', 'json', 'threading', 'logging'],
    hookspath=[str(PROJECT_ROOT / 'packaging/hooks')],
    hooksconfig={}, runtime_hooks=[], excludes=EXCLUDES, noarchive=False,
)
pyz = PYZ(a.pure)
if DEVELOPMENT:
    exe = EXE(
        pyz, a.scripts, [], exclude_binaries=True, name=NAME,
        debug=False, strip=False, upx=False, console=True,
        icon=str(SOURCE / 'ico/ico.png'),
    )
    coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name=NAME)
else:
    exe = EXE(
        pyz, a.scripts, a.binaries, a.datas, [], name=NAME,
        debug=False, strip=False, upx=False, console=False,
        icon=str(SOURCE / 'ico/ico.png'),
    )
