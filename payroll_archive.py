"""
payroll_archive.py - 월별 출력·보고 파일 탐색 및 스냅샷 요약
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from excel_writer import OUTPUT_DIR
from leave_usage_ledger import LEAVE_USAGE_LEDGER_DIR, get_leave_usage_ledger_path
from payroll_comparison import PAYROLL_DIFF_DIR, SNAPSHOT_FILENAME
from core.labels import label_for_filename
from roster_constants import norm_name_key

BASE_DIR = Path(__file__).resolve().parent

# payroll_snapshot.json은 페이지 전환/필터 변경마다 여러 번 읽힐 수 있어 캐시합니다.
# key=(path, mtime) → records
_SNAPSHOT_CACHE: dict[tuple[str, float], list[dict[str, Any]]] = {}
_SNAPSHOT_CACHE_MAX = 24

# 월별 output 폴더에 있을 수 있는 주요 파일
OUTPUT_FILE_LABELS: dict[str, str] = {
    "급여대장.xlsx": "급여대장",
    "급여명세서.xlsx": "급여명세서",
    "지급내역.xlsx": "지급내역",
    "payroll_snapshot.json": "급여 스냅샷",
}


@dataclass
class ArchiveFile:
    path: Path
    label: str
    category: str  # output | comparison | leave | other
    period: str | None = None
    size_kb: float = 0.0
    modified: str = ""


@dataclass
class MonthSummary:
    period: str
    employee_count: int = 0
    total_gross: int = 0
    total_net: int = 0
    total_deduction: int = 0
    leave_users: int = 0
    absence_users: int = 0
    has_output: bool = False
    has_comparison: bool = False
    files: list[ArchiveFile] = field(default_factory=list)


def _dedupe_record_rank(rec: dict[str, Any]) -> tuple[int, int]:
    """중복 인원 병합 시 우선순위: 총지급액 → 대표 사업장 폴더(한국앰코)."""
    from core.org_config import canonical_scope_workplace

    gross = int(rec.get("gross_pay") or 0)
    scope_wp = str(rec.get("_scope_workplace") or "").strip()
    prefer_canonical_folder = 1 if scope_wp and scope_wp == canonical_scope_workplace(scope_wp) else 0
    return (gross, prefer_canonical_folder)


def dedupe_monthly_snapshot_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    동일 급여월에 여러 사업장 폴더로 중복 산출된 스냅샷을 1인 1건으로 합칩니다.

    예: 한국앰코·한국앰코생산에 같은 26명이 각각 있으면 52명 → 26명.
    """
    best: dict[tuple[str, str], dict[str, Any]] = {}
    for r in records:
        name_key = norm_name_key(r.get("name"))
        if not name_key:
            continue
        affiliate = str(r.get("affiliate") or "").strip()
        key = (affiliate, name_key)
        prev = best.get(key)
        if prev is None:
            best[key] = r
            continue
        if _dedupe_record_rank(r) >= _dedupe_record_rank(prev):
            best[key] = r
    return sorted(
        best.values(),
        key=lambda x: (str(x.get("workplace") or ""), str(x.get("name") or "")),
    )


def _period_sort_key(period: str) -> tuple[int, int]:
    try:
        y, m = period.split("-")
        return int(y), int(m)
    except ValueError:
        return 0, 0


def list_payroll_periods() -> list[str]:
    """급여 scope key 목록 (최신순)."""
    from services.payroll_scope import discover_scopes

    scopes = discover_scopes()
    if scopes:
        return [s.key for s in scopes]
    if not OUTPUT_DIR.exists():
        return []
    periods: list[str] = []
    for p in OUTPUT_DIR.iterdir():
        if p.is_dir() and _period_sort_key(p.name) != (0, 0):
            periods.append(p.name)
    periods.sort(key=_period_sort_key, reverse=True)
    return periods


def _file_info(path: Path, label: str, category: str, period: str | None) -> ArchiveFile:
    stat = path.stat()
    return ArchiveFile(
        path=path,
        label=label,
        category=category,
        period=period,
        size_kb=round(stat.st_size / 1024, 1),
        modified=datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
    )


def collect_files_for_period(period: str, scope=None) -> list[ArchiveFile]:
    """한 달치 생성·관련 파일 목록."""
    from services.payroll_scope import PayrollScope, resolve_output_dir

    if scope is None:
        scope = PayrollScope.try_parse_key(period)
    files: list[ArchiveFile] = []

    if isinstance(scope, PayrollScope):
        out_dir = resolve_output_dir(scope)
        period = scope.period
    else:
        out_dir = OUTPUT_DIR / period
    if out_dir.is_dir():
        for p in sorted(out_dir.iterdir()):
            if not p.is_file():
                continue
            label = OUTPUT_FILE_LABELS.get(p.name, label_for_filename(p.name))
            cat = "output"
            if "전월대비" in p.name:
                label = "전월대비 급여차이 보고"
                cat = "comparison"
            elif "급여스냅샷" in p.name:
                label = "급여 스냅샷 (엑셀)" if p.suffix == ".xlsx" else "급여 스냅샷 (CSV)"
                cat = "comparison"
            files.append(_file_info(p, label, cat, period))
        for p in sorted(out_dir.glob("급여대장_추가*.xlsx")):
            files.append(_file_info(p, label_for_filename(p.name), "output", period))

    if PAYROLL_DIFF_DIR.is_dir() and not isinstance(scope, PayrollScope):
        for p in sorted(PAYROLL_DIFF_DIR.glob(f"{period}_*")):
            if p.is_file():
                if "전월대비" in p.name:
                    lbl = "전월대비 급여차이 보고"
                elif "급여스냅샷" in p.name and p.suffix == ".xlsx":
                    lbl = "급여 스냅샷 (엑셀)"
                elif "급여스냅샷" in p.name and p.suffix == ".csv":
                    lbl = "급여 스냅샷 (CSV)"
                else:
                    lbl = label_for_filename(p.name)
                files.append(_file_info(p, lbl, "comparison", period))

    ledger = get_leave_usage_ledger_path()
    if ledger.exists():
        files.append(_file_info(ledger, "연차사용대장 (통합)", "leave", None))

    return files


def load_snapshot_records(period: str, scope=None) -> list[dict[str, Any]]:
    from services.payroll_scope import PayrollScope, discover_scopes, resolve_output_dir

    def _read(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        try:
            mtime = path.stat().st_mtime
        except OSError:
            mtime = 0.0
        key = (str(path), float(mtime))
        cached = _SNAPSHOT_CACHE.get(key)
        if cached is not None:
            return cached
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            recs = data.get("records") or []
            out = recs if isinstance(recs, list) else []
            _SNAPSHOT_CACHE[key] = out
            if len(_SNAPSHOT_CACHE) > _SNAPSHOT_CACHE_MAX:
                for k in list(_SNAPSHOT_CACHE.keys())[: max(1, len(_SNAPSHOT_CACHE) - _SNAPSHOT_CACHE_MAX)]:
                    _SNAPSHOT_CACHE.pop(k, None)
            return out
        except (json.JSONDecodeError, OSError):
            return []

    # scope가 None이면 “YYYY-MM(월)” 단위로 해당 월의 모든 scope 스냅샷을 합칩니다.
    # (기존: PayrollScope.try_parse_key()의 기본 계열사/사업장으로 한정되어 org filter가 무력화되는 문제)
    if scope is None:
        if "\x1f" in str(period):
            scope = PayrollScope.try_parse_key(period)
        else:
            out: list[dict[str, Any]] = []
            for s in discover_scopes():
                if s.period != period:
                    continue
                for rec in _read(resolve_output_dir(s) / SNAPSHOT_FILENAME):
                    if isinstance(rec, dict):
                        tagged = dict(rec)
                        tagged["_scope_workplace"] = s.workplace
                        out.append(tagged)
                    else:
                        out.append(rec)
            return dedupe_monthly_snapshot_records(out)

    if isinstance(scope, PayrollScope):
        return _read(resolve_output_dir(scope) / SNAPSHOT_FILENAME)

    # scope가 PayrollScope가 아닌 경우(레거시/예외)는 기존 로직 유지
    path = OUTPUT_DIR / period / SNAPSHOT_FILENAME
    if not path.exists():
        for s in discover_scopes():
            if s.period == period:
                path = resolve_output_dir(s) / SNAPSHOT_FILENAME
                break
    return _read(path)


def build_month_summary(period: str) -> MonthSummary:
    from services.payroll_scope import PayrollScope
    # scope.key(= \x1f 포함)면 기존처럼 해당 scope 기준으로 계산
    # YYYY-MM(월)만 들어오면 “해당 월의 모든 scope”를 합산합니다.
    if "\x1f" not in str(period):
        records = load_snapshot_records(period, None)
        has_output = bool(records)

        # 전월대비 보고서 존재 여부(상태용)만 대략 판별
        has_comparison = any(PAYROLL_DIFF_DIR.glob(f"{period}_전월대비*.xlsx"))
        if not has_comparison:
            from services.payroll_scope import discover_scopes, resolve_output_dir

            for s in discover_scopes():
                out_dir = resolve_output_dir(s)
                if any(out_dir.glob(f"{period}_전월대비*.xlsx")):
                    has_comparison = True
                    break

        summary = MonthSummary(period=period, files=[], has_output=has_output, has_comparison=has_comparison)
        if not records:
            return summary

        summary.employee_count = len(records)
        for r in records:
            summary.total_gross += int(r.get("gross_pay") or 0)
            summary.total_net += int(r.get("net_pay") or 0)
            summary.total_deduction += int(r.get("total_deduction") or 0)
            if float(r.get("leave_days") or 0) > 0:
                summary.leave_users += 1
            if float(r.get("unpaid_days") or 0) > 0:
                summary.absence_users += 1
        return summary

    scope = PayrollScope.try_parse_key(period)
    records = load_snapshot_records(period, scope)
    files = collect_files_for_period(period, scope)

    display_period = scope.period if scope else period
    summary = MonthSummary(
        period=display_period,
        files=files,
        has_output=any(f.category == "output" for f in files),
    )
    summary.has_comparison = any("전월대비" in f.label for f in files)

    if not records:
        return summary

    summary.employee_count = len(records)
    for r in records:
        summary.total_gross += int(r.get("gross_pay") or 0)
        summary.total_net += int(r.get("net_pay") or 0)
        summary.total_deduction += int(r.get("total_deduction") or 0)
        if float(r.get("leave_days") or 0) > 0:
            summary.leave_users += 1
        if float(r.get("unpaid_days") or 0) > 0:
            summary.absence_users += 1
    return summary


def format_period_display(period: str) -> str:
    try:
        y, m = period.split("-")
        return f"{y}년 {int(m):02d}월"
    except ValueError:
        return period


def format_executive_report_title(period: str) -> str:
    """월별 보고 제목 — 예: 2026년 5월 인도급 급여 요약."""
    try:
        y, m = period.split("-")
        return f"{y}년 {int(m)}월 인도급 급여 요약"
    except ValueError:
        return f"{period} 인도급 급여 요약"


def format_ytd_range_label(periods: list[str]) -> str:
    """연간 구간 라벨 — 예: 2026년 1~5월."""
    if not periods:
        return ""
    try:
        y0, m0 = periods[0].split("-")
        y1, m1 = periods[-1].split("-")
        mi, ma = int(m0), int(m1)
        if mi == ma:
            return f"{y0}년 {mi}월"
        return f"{y0}년 {mi}~{ma}월"
    except ValueError:
        return ""
