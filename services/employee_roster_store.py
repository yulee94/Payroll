"""
services/employee_roster_store.py - 프로그램 내 직원 명부 (읽기·저장·메타·캐시)
"""

from __future__ import annotations

import copy
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from excel_writer import TEMPLATES_DIR
from payroll_builder import ROSTER_FILENAME, get_templates_roster_path
from roster_constants import ROSTER_HEADER_ALIASES
from bank_account import enrich_roster_bank_info
from roster_workbook import (
    load_employee_roster_from_workbook,
    roster_dict_to_list,
    save_employee_roster_records,
)

META_FILENAME = ".roster_meta.json"
ROSTER_BACKUP_NAME = "근로자명부_자동백업.xlsx"

_cache_key: str = ""
_cache_mtime: float = 0.0
_cache_rows: list[dict[str, Any]] | None = None
_cache_dict: dict[str, dict[str, Any]] | None = None

MONTHLY_ROSTER_PREFIX = "근로자명부_"


def canonical_roster_path() -> Path:
    """현재 운영 명부 (6월 이후 갱신). templates/근로자명부.xlsx."""
    found = get_templates_roster_path()
    if found is not None:
        return found
    return TEMPLATES_DIR / ROSTER_FILENAME


def roster_path_for_period(period: str = "") -> Path:
    """2026-01~05 월별 스냅샷이 있으면 해당 파일, 없으면 canonical."""
    period = str(period or "").strip()
    if period:
        tagged = TEMPLATES_DIR / f"{MONTHLY_ROSTER_PREFIX}{period}.xlsx"
        if tagged.is_file():
            return tagged
    return canonical_roster_path()


def invalidate_roster_cache() -> None:
    global _cache_key, _cache_mtime, _cache_rows, _cache_dict
    _cache_key = ""
    _cache_mtime = 0.0
    _cache_rows = None
    _cache_dict = None


def _file_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def _meta_path() -> Path:
    return TEMPLATES_DIR / META_FILENAME


def _read_meta() -> dict[str, Any]:
    path = _meta_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _write_meta(extra: dict[str, Any] | None = None) -> None:
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    meta = _read_meta()
    meta["updated_at"] = datetime.now().isoformat(timespec="seconds")
    meta["path"] = str(canonical_roster_path().name)
    if extra:
        meta.update(extra)
    _meta_path().write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def roster_updated_display() -> str:
    """UI용 최종 갱신 시각."""
    meta = _read_meta()
    raw = str(meta.get("updated_at") or "").strip()
    if raw:
        try:
            dt = datetime.fromisoformat(raw)
            return dt.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            return raw
    path = canonical_roster_path()
    if path.is_file():
        return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    return "미등록"


def roster_exists() -> bool:
    return canonical_roster_path().is_file()


def _period_hint_from_path(path: Path) -> str:
    name = path.stem
    if name.startswith(MONTHLY_ROSTER_PREFIX) and len(name) == len(MONTHLY_ROSTER_PREFIX) + 7:
        return name[len(MONTHLY_ROSTER_PREFIX) :]
    return ""


def _refresh_cache(path: Path, *, period_hint: str = "") -> None:
    global _cache_key, _cache_mtime, _cache_rows, _cache_dict
    hint = period_hint or _period_hint_from_path(path)
    roster_dict = load_employee_roster_from_workbook(
        path, detect_formulas=False, period_hint=hint
    )
    rows = roster_dict_to_list(roster_dict)
    enrich_roster_bank_info(rows)
    _cache_key = f"{path.resolve()}|{hint}"
    _cache_mtime = _file_mtime(path)
    _cache_rows = rows
    _cache_dict = roster_dict


def get_cached_roster_dict(
    path: Path | None = None,
    *,
    period_hint: str = "",
) -> dict[str, dict[str, Any]] | None:
    """청구서 산출용 — 캐시가 유효하면 재파싱 없이 반환."""
    roster_path = path or canonical_roster_path()
    if not roster_path.is_file():
        return None
    hint = period_hint or _period_hint_from_path(roster_path)
    mtime = _file_mtime(roster_path)
    key = f"{roster_path.resolve()}|{hint}"
    if _cache_dict is not None and _cache_key == key and _cache_mtime == mtime:
        return _cache_dict
    _refresh_cache(roster_path, period_hint=hint)
    return _cache_dict


def load_roster_rows(*, force: bool = False) -> list[dict[str, Any]]:
    path = canonical_roster_path()
    if not path.is_file():
        invalidate_roster_cache()
        return []

    hint = _period_hint_from_path(path)
    mtime = _file_mtime(path)
    key = f"{path.resolve()}|{hint}"
    if not force and _cache_rows is not None and _cache_key == key and _cache_mtime == mtime:
        return copy.deepcopy(_cache_rows)

    _refresh_cache(path, period_hint=hint)
    return copy.deepcopy(_cache_rows or [])


def save_roster_rows(rows: list[dict[str, Any]], *, note: str = "") -> int:
    """명부 저장 + 자동 백업. 저장된 인원 수 반환."""
    path = canonical_roster_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.is_file():
        backup = path.parent / ROSTER_BACKUP_NAME
        shutil.copy2(path, backup)

    if not path.is_file():
        _create_empty_roster_workbook(path)

    count = save_employee_roster_records(path, rows)
    invalidate_roster_cache()
    try:
        from core.access_control import invalidate_executive_index

        invalidate_executive_index()
    except ImportError:
        pass
    _refresh_cache(path)
    _write_meta({"employee_count": count, "note": note or "프로그램에서 저장"})
    return count


def import_roster_from_file(source: Path) -> int:
    """외부 엑셀을 명부로 가져와 덮어씁니다."""
    if not source.is_file():
        raise FileNotFoundError("가져올 파일을 찾을 수 없습니다.")
    dest = canonical_roster_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file():
        shutil.copy2(dest, dest.parent / ROSTER_BACKUP_NAME)
    shutil.copy2(source, dest)
    invalidate_roster_cache()
    rows = load_roster_rows(force=True)
    _write_meta(
        {
            "employee_count": len(rows),
            "note": f"가져오기: {source.name}",
            "imported_from": source.name,
        }
    )
    return len(rows)


def _create_empty_roster_workbook(path: Path) -> None:
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "씨엔엘"
    for col, (_canonical, aliases) in enumerate(ROSTER_HEADER_ALIASES.items(), start=1):
        ws.cell(1, col, aliases[0])
    wb.save(path)
    wb.close()
