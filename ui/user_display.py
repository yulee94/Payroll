"""
ui/user_display.py - 사용자 화면용 문구 정리 (경로·기술 정보 숨김)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from core.labels import label_for_filename
from payroll_archive import format_period_display

_PATH_RE = re.compile(
    r"(?:[A-Za-z]:\\(?:[^\s\n\r\"<>|]+|\\.)+|\\\\[^\s\n\r\"<>|]+)"
)


def strip_paths(text: str) -> str:
    if not text:
        return ""
    cleaned = _PATH_RE.sub("", text)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"[:：]\s*$", "", cleaned.strip())
    return cleaned.strip()


def friendly_document_title(path: Path | None, sheet: str = "", period: str = "") -> str:
    if path is None:
        return "문서"
    title = label_for_filename(path.name)
    if period:
        title = f"{format_period_display(period)} · {title}"
    if sheet and sheet not in ("Sheet1", "Sheet", "시트1"):
        title = f"{title} ({sheet})"
    return title


def sanitize_warning(message: str) -> str:
    msg = strip_paths(message).strip()
    if not msg:
        return ""

    replacements = [
        (r"templates[/\\]", ""),
        (r"employees[/\\]", ""),
        (r"output[/\\]", ""),
        (r"※\s*", ""),
        (r"\(\s*5행부터 C열=성명\s*\)", ""),
        (r"(\d+)행:", r"\1번째 줄 —"),
        ("templates/근로자명부.xlsx", "근로자 명부"),
        ("근로자명부.xlsx", "근로자 명부"),
        ("명부 '수당'", "명부 수당"),
        ("명부 '통상시급'", "명부 통상시급"),
        ("지급내역양식", "지급내역"),
        ("급여차이내역 폴더", "급여차이 보고"),
        ("Permission denied", "파일이 사용 중이거나 저장할 수 없습니다"),
        ("PermissionError", ""),
    ]
    for old, new in replacements:
        if old.startswith("("):
            msg = re.sub(old, new, msg)
        else:
            msg = msg.replace(old, new)

    msg = re.sub(r"\s{2,}", " ", msg).strip(" ·—")
    return msg


def sanitize_warnings(messages: list[str], limit: int = 10) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in messages:
        msg = sanitize_warning(raw)
        if not msg or msg in seen:
            continue
        seen.add(msg)
        out.append(msg)
        if len(out) >= limit:
            break
    return out


def format_validation_error(exc: BaseException) -> str:
    from validator import PayrollValidationError

    if isinstance(exc, PayrollValidationError):
        lines = sanitize_warnings(exc.messages, limit=8)
        return "\n".join(lines) if lines else "입력 내용을 확인해 주세요."
    return friendly_error(exc)


def friendly_error(exc: BaseException) -> str:
    from validator import PayrollValidationError

    if isinstance(exc, PayrollValidationError):
        return format_validation_error(exc)

    name = type(exc).__name__
    msg = strip_paths(str(exc).strip())

    if name in ("PermissionError", "OSError") and ("denied" in msg.lower() or "permission" in msg.lower()):
        return "파일이 다른 프로그램에서 열려 있거나 저장할 수 없습니다."
    if name == "FileNotFoundError" or "찾을 수 없" in msg:
        return "파일을 찾을 수 없습니다."
    if not msg or name in msg:
        return "처리 중 문제가 발생했습니다. 잠시 후 다시 시도해 주세요."
    if len(msg) > 180:
        msg = msg[:180].rstrip() + "…"
    return msg


def format_save_success(path: Path | str) -> str:
    return f"「{label_for_filename(Path(path).name)}」을(를) 저장했습니다."


def format_result_summary(info: dict[str, Any]) -> str:
    scope = info.get("scope")
    p = info.get("paths") or {}
    if scope is not None:
        from services.payroll_scope import PayrollScope

        if isinstance(scope, PayrollScope):
            period_label = scope.display_label()
        else:
            period_label = str(scope)
    elif p.get("ledger"):
        period_label = p["ledger"].parent.name
    else:
        period_label = ""

    lines = [
        f"✓ {period_label} — {info.get('count', 0)}명 처리 완료",
        "",
        "생성된 자료",
        "  · 급여대장",
        "  · 급여명세서",
        "  · 지급내역",
    ]

    if p.get("ledger_extra"):
        lines.append(f"  · 급여대장 (추가 {len(p['ledger_extra'])}건)")

    comp = info.get("comparison") or {}
    if comp.get("path"):
        lines.append("  · 전월 대비 급여차이 보고")

    ll = info.get("leave_ledger") or {}
    if ll.get("written") or ll.get("monthly_written"):
        lines.append("  · 연차사용대장 갱신")

    lines.append("")
    lines.append(f"「월별 자료함」에서 {period_label} 자료를 확인할 수 있습니다.")

    warns = sanitize_warnings(info.get("warnings") or [], limit=8)
    if warns:
        lines.append("")
        lines.append("확인이 필요한 사항")
        for w in warns:
            lines.append(f"  · {w}")
        extra = len(info.get("warnings") or []) - len(warns)
        if extra > 0:
            lines.append(f"  · 외 {extra}건")

    return "\n".join(lines)


def format_reports_guide(period: str, summary: Any) -> str:
    lines = [
        format_period_display(period),
        "",
        "전월 대비 급여차이",
    ]
    comp_files = [f for f in summary.files if "전월대비" in f.label]
    if comp_files:
        f = comp_files[-1]
        lines.append(f"  · 생성됨 ({f.modified})")
        lines.append("  · 오른쪽 미리보기에서 내용을 확인하세요.")
    else:
        lines.append("  · 아직 없습니다. (첫 달은 전월 데이터가 없을 수 있습니다)")

    lines.extend(["", "연차사용대장", "  · 통합 연차사용대장이 유지됩니다.", "  · 「연차대장 열기」로 확인"])

    lines.extend(["", "당월 급여 현황"])
    if summary.employee_count:
        lines.append(f"  · 인원 {summary.employee_count}명")
        lines.append(f"  · 총지급 {summary.total_gross:,}원")
        lines.append(f"  · 실수령 {summary.total_net:,}원")
        lines.append(f"  · 연차 {summary.leave_users}명 · 무급/결근 {summary.absence_users}명")
    else:
        lines.append("  · 급여 산출 후 자동으로 표시됩니다.")

    return "\n".join(lines)


def preview_status_line(
    *,
    sheet: str = "",
    truncated: bool = False,
    truncated_cols: bool = False,
    row_count: int = 0,
) -> str:
    parts: list[str] = []
    if sheet and sheet not in ("Sheet1", "Sheet"):
        parts.append(f"시트: {sheet}")
    if row_count:
        parts.append(f"{row_count}행")
    if truncated_cols:
        parts.append("열 일부만 표시 · Excel 내려받기로 전체 확인")
    elif truncated:
        parts.append("행 일부만 표시 · Excel 내려받기로 전체 확인")
    parts.append("←→ 하단 스크롤 또는 Shift+휠로 좌우 이동")
    return "  ·  ".join(parts) if parts else ""
