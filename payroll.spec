# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 빌드: pyinstaller payroll.spec
# 결과: dist/급여프로그램.exe

import sys
from pathlib import Path

block_cipher = None
base = Path(SPECPATH)


def _collect_tree(folder: str) -> list[tuple[str, str]]:
    """폴더 복사 — Excel 잠금(~$) 파일 제외."""
    src_root = base / folder
    if not src_root.is_dir():
        return []
    rows: list[tuple[str, str]] = []
    for path in src_root.rglob("*"):
        if not path.is_file():
            continue
        if path.name.startswith("~$"):
            continue
        rel = path.relative_to(src_root).as_posix()
        rows.append((str(path), f"{folder}/{rel}"))
    return rows


_datas: list[tuple[str, str]] = []
for _folder in ("templates", "employees", "assets", "config", "locales"):
    _datas.extend(_collect_tree(_folder))

_registry = base / "users" / "registry.json"
if _registry.is_file():
    _datas.append((str(_registry), "users"))
_tenants = base / "tenants.json"
if _tenants.is_file():
    _datas.append((str(_tenants), "."))

a = Analysis(
    ['main.py'],
    pathex=[str(base)],
    binaries=[],
    datas=_datas,
    hiddenimports=[
        'openpyxl',
        'windnd',
        'matplotlib',
        'matplotlib.backends.backend_tkagg',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'httpx',
        'httpcore',
        'certifi',
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
    name='COSS_Payroll',
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
)
