"""
core/file_save.py - Excel·파일 저장 (잠금·권한 오류 완화)
"""

from __future__ import annotations

import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from openpyxl import Workbook


def resolve_writable_path(path: Path) -> Path:
    """
    대상 파일이 이미 있거나 잠긴 경우 같은 폴더에 _1, _2 … 이름을 붙입니다.
  """
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    for i in range(1, 50):
        candidate = parent / f"{stem}_{i}{suffix}"
        if not candidate.exists():
            return candidate
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return parent / f"{stem}_{ts}{suffix}"


def copy_template(template: Path, dest: Path) -> Path:
    """양식 복사. 대상이 잠기면 대체 경로를 사용합니다."""
    if not template.is_file():
        raise FileNotFoundError(f"양식 파일을 찾을 수 없습니다: {template.name}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    target = dest
    if target.exists():
        try:
            target.unlink()
        except OSError:
            target = resolve_writable_path(dest)
    shutil.copy2(template, target)
    return target


def save_workbook(wb: Workbook, path: Path) -> Path:
    """워크북 저장. 잠금 시 대체 파일명·임시 파일 교체를 시도합니다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    candidates: list[Path] = [path]
    if path.exists():
        candidates.append(resolve_writable_path(path))

    last_exc: OSError | None = None
    for target in candidates:
        fd, tmp_name = tempfile.mkstemp(suffix=target.suffix, dir=target.parent)
        os.close(fd)
        tmp = Path(tmp_name)
        try:
            wb.save(tmp)
            try:
                if target.exists():
                    target.unlink()
            except OSError:
                target = resolve_writable_path(target)
            tmp.replace(target)
            return target
        except OSError as exc:
            last_exc = exc
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
    if last_exc is not None:
        raise last_exc
    raise OSError(f"저장할 수 없습니다: {path.name}")


def stage_readable_copy(source: Path) -> Path:
    """업로드 원본이 Excel에서 열려 있어도 읽을 수 있도록 임시 복사본을 만듭니다."""
    if not source.is_file():
        raise FileNotFoundError(str(source))
    tmp_dir = Path(tempfile.gettempdir()) / "bitween_payroll_upload"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    dest = tmp_dir / source.name
    shutil.copy2(source, dest)
    return dest
