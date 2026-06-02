"""
services/upload_undo.py - 마지막 급여 산출 되돌리기
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from excel_writer import OUTPUT_DIR
from services.payroll_scope import PayrollScope

UNDO_FILENAME = ".last_upload.json"


def _undo_path() -> Path:
    return OUTPUT_DIR / UNDO_FILENAME


def record_upload(scope: PayrollScope, created_paths: list[Path], invoice_name: str = "") -> None:
    files = [str(p) for p in created_paths if p and p.exists()]
    payload = {
        "scope": {
            "affiliate": scope.affiliate,
            "workplace": scope.workplace,
            "period": scope.period,
        },
        "created_files": files,
        "invoice_name": invoice_name,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
    }
    _undo_path().write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def can_undo() -> bool:
    data = _load()
    return bool(data and data.get("created_files"))


def peek_undo() -> dict[str, Any] | None:
    return _load()


def scope_from_undo(data: dict[str, Any] | None) -> PayrollScope | None:
    if not data:
        return None
    scope_data = data.get("scope") or {}
    period = str(scope_data.get("period") or "").strip()
    if not period:
        return None
    return PayrollScope(
        str(scope_data.get("affiliate") or ""),
        str(scope_data.get("workplace") or ""),
        period,
    )


def build_undo_warning_message(scope: PayrollScope, data: dict[str, Any] | None) -> str:
    """1차 확인 — 영구 삭제 경고."""
    file_count = len((data or {}).get("created_files") or [])
    invoice = str((data or {}).get("invoice_name") or "").strip()
    lines = [
        "【주의】 되돌리기는 삭제된 파일·데이터를 복구할 수 없습니다.",
        "",
        f"대상: {scope.display_label()}",
        "",
        "다음 항목이 영구 삭제될 수 있습니다.",
        "  · 급여대장 · 급여명세서 · 지급내역",
        "  · 도급비 청구서 원본",
        "  · 급여 스냅샷 · 전월 대비 보고 등 산출 파일",
    ]
    if file_count:
        lines.append(f"  · 기록된 파일 {file_count}건")
    if invoice:
        lines.append(f"  · 청구서: {invoice}")
    lines.extend(
        [
            "",
            "휴지통으로 이동하지 않으며, 실수로 되돌린 경우에도",
            "프로그램에서 이전 파일을 다시 불러올 수 없습니다.",
            "",
            "연차사용대장은 자동으로 되돌리지 않습니다.",
            "",
            "위 내용을 확인했으면 「확인」을 눌러 다음 단계로 진행하세요.",
        ]
    )
    return "\n".join(lines)


def build_undo_final_confirm_message(scope: PayrollScope) -> str:
    """2차 확인 — 최종 동의."""
    return (
        f"{scope.display_label()}\n\n"
        "정말 되돌리시겠습니까?\n\n"
        "「예」를 선택하면 위 급여월의 산출 파일·데이터가 "
        "영구 삭제되며 되돌릴 수 없습니다."
    )


def undo_last_upload() -> PayrollScope:
    data = _load()
    if not data:
        raise FileNotFoundError("되돌릴 산출 내역이 없습니다.")

    scope_data = data.get("scope") or {}
    scope = PayrollScope(
        str(scope_data.get("affiliate") or ""),
        str(scope_data.get("workplace") or ""),
        str(scope_data.get("period") or ""),
    )

    for raw in data.get("created_files") or []:
        path = Path(raw)
        if not path.exists():
            continue
        if path.is_file():
            path.unlink(missing_ok=True)
        elif path.is_dir():
            import shutil

            shutil.rmtree(path, ignore_errors=True)

    out_dir = scope.output_dir()
    if out_dir.is_dir() and not any(out_dir.iterdir()):
        out_dir.rmdir()
        wp_dir = out_dir.parent
        if wp_dir.is_dir() and not any(wp_dir.iterdir()):
            wp_dir.rmdir()
            aff_dir = wp_dir.parent
            if aff_dir.is_dir() and aff_dir != OUTPUT_DIR and not any(aff_dir.iterdir()):
                aff_dir.rmdir()

    legacy = OUTPUT_DIR / scope.period
    if legacy.is_dir() and legacy == out_dir or (legacy.is_dir() and not any(legacy.iterdir())):
        import shutil

        shutil.rmtree(legacy, ignore_errors=True)

    if _undo_path().is_file():
        _undo_path().unlink(missing_ok=True)

    return scope


def _load() -> dict[str, Any] | None:
    path = _undo_path()
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, OSError):
        return None
