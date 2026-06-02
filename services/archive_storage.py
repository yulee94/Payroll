"""
services/archive_storage.py - 월별 자료함 저장 (청구서 원본·매니페스트)
"""

from __future__ import annotations

import json
import shutil
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from core.org_config import get_default_affiliate, list_config_workplaces
from excel_writer import OUTPUT_DIR
from payroll_archive import load_snapshot_records
from services.org_registry import enrich_records, resolve_affiliate, resolve_workplace
from services.payroll_scope import PayrollScope, resolve_output_dir

MANIFEST_FILENAME = "payroll_manifest.json"
INVOICE_STORED_NAME = "도급비청구서.xlsx"

PAYROLL_OUTPUT_NAMES = ("급여대장.xlsx", "급여명세서.xlsx", "지급내역.xlsx")


def _mode_label(values: list[str], default: str) -> str:
    cleaned = [v.strip() for v in values if v and v.strip()]
    if not cleaned:
        return default
    return Counter(cleaned).most_common(1)[0][0]


def _resolve_period_workplace(enriched: list[dict[str, Any]], affiliate: str) -> str:
    explicit = [str(r.get("workplace") or "").strip() for r in enriched if str(r.get("workplace") or "").strip()]
    if explicit:
        return _mode_label(explicit, "미분류")
    cfg = list_config_workplaces(affiliate or "")
    if len(cfg) == 1:
        return cfg[0]
    return _mode_label([resolve_workplace(r) for r in enriched], "미분류")


def scope_output_dir(scope: PayrollScope) -> Path:
    return resolve_output_dir(scope)


def save_period_invoice(
    invoice_path: Path,
    scope: PayrollScope,
    records: list[dict[str, Any]],
    *,
    original_name: str | None = None,
) -> Path:
    """청구서 원본을 계열사/사업장/월 폴더에 저장."""
    source = Path(invoice_path)
    if not source.is_file():
        raise FileNotFoundError(f"청구서 원본을 찾을 수 없습니다: {invoice_path}")

    out_dir = resolve_output_dir(scope)
    out_dir.mkdir(parents=True, exist_ok=True)
    from core.file_save import resolve_writable_path

    dest = out_dir / INVOICE_STORED_NAME
    if dest.exists():
        try:
            dest.unlink()
        except OSError:
            dest = resolve_writable_path(dest)
    shutil.copy2(source, dest)

    enriched = enrich_records(records)
    affiliate = scope.affiliate or _mode_label([resolve_affiliate(r) for r in enriched], get_default_affiliate())
    workplace = scope.workplace or _resolve_period_workplace(enriched, affiliate)

    manifest = load_scope_manifest(scope)
    manifest.update(
        {
            "period": scope.period,
            "affiliate": affiliate,
            "workplace": workplace,
            "invoice_file": INVOICE_STORED_NAME,
            "invoice_original_name": original_name or source.name,
            "saved_at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    _write_manifest(out_dir, manifest)
    return dest


def _write_manifest(out_dir: Path, manifest: dict[str, Any]) -> None:
    path = out_dir / MANIFEST_FILENAME
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def update_scope_manifest(scope: PayrollScope, **fields: Any) -> None:
    """월별 매니페스트에 필드를 병합 저장합니다."""
    out_dir = resolve_output_dir(scope)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = load_scope_manifest(scope)
    manifest.update(fields)
    _write_manifest(out_dir, manifest)


def load_scope_manifest(scope: PayrollScope) -> dict[str, Any]:
    out_dir = resolve_output_dir(scope)
    path = out_dir / MANIFEST_FILENAME
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            pass
    return infer_scope_manifest(scope)


def load_period_manifest(period: str) -> dict[str, Any]:
    """하위 호환 — period만 알 때 (discover_scopes 호출 없이 디렉터리 직접 탐색)."""
    import re

    period_re = re.compile(r"^\d{4}-\d{2}$")
    if not period_re.match(period):
        return infer_scope_manifest(PayrollScope(get_default_affiliate(), "미분류", period))

    legacy_scope = PayrollScope(get_default_affiliate(), "미분류", period)
    if (OUTPUT_DIR / period).is_dir() and period_has_payroll_outputs(period, legacy_scope):
        return load_scope_manifest(legacy_scope)

    if OUTPUT_DIR.exists():
        for affiliate_dir in sorted(OUTPUT_DIR.iterdir()):
            if not affiliate_dir.is_dir() or affiliate_dir.name.startswith("."):
                continue
            if period_re.match(affiliate_dir.name):
                continue
            for workplace_dir in sorted(affiliate_dir.iterdir()):
                if not workplace_dir.is_dir():
                    continue
                period_dir = workplace_dir / period
                if not period_dir.is_dir():
                    continue
                scope = PayrollScope(affiliate_dir.name, workplace_dir.name, period)
                if period_has_payroll_outputs(period, scope):
                    return load_scope_manifest(scope)

    return infer_scope_manifest(legacy_scope)


def infer_scope_manifest(scope: PayrollScope) -> dict[str, Any]:
    out_dir = resolve_output_dir(scope)
    enriched = enrich_records(load_snapshot_records(scope.period, scope))
    affiliate = scope.affiliate or _mode_label([resolve_affiliate(r) for r in enriched], get_default_affiliate())
    workplace = scope.workplace or _resolve_period_workplace(enriched, affiliate)

    invoice_file = ""
    for candidate in (INVOICE_STORED_NAME, "청구서.xlsx"):
        if (out_dir / candidate).is_file():
            invoice_file = candidate
            break

    return {
        "period": scope.period,
        "affiliate": affiliate,
        "workplace": workplace,
        "invoice_file": invoice_file,
        "invoice_original_name": "",
    }


def infer_period_manifest(period: str) -> dict[str, Any]:
    return infer_scope_manifest(PayrollScope(get_default_affiliate(), "", period))


def period_has_payroll_outputs(period: str, scope: PayrollScope | None = None) -> bool:
    if scope:
        out_dir = resolve_output_dir(scope)
        return any((out_dir / name).is_file() for name in PAYROLL_OUTPUT_NAMES)
    legacy = OUTPUT_DIR / period
    return any((legacy / name).is_file() for name in PAYROLL_OUTPUT_NAMES)


def ensure_scope_manifest(scope: PayrollScope) -> None:
    out_dir = resolve_output_dir(scope)
    path = out_dir / MANIFEST_FILENAME
    if not path.is_file() and period_has_payroll_outputs(scope.period, scope):
        _write_manifest(out_dir, infer_scope_manifest(scope))


def ensure_period_manifest(period: str) -> None:
    import re

    period_re = re.compile(r"^\d{4}-\d{2}$")
    if not period_re.match(period):
        return

    legacy_scope = PayrollScope(get_default_affiliate(), "미분류", period)
    if (OUTPUT_DIR / period).is_dir():
        ensure_scope_manifest(legacy_scope)

    if not OUTPUT_DIR.exists():
        return

    for affiliate_dir in OUTPUT_DIR.iterdir():
        if not affiliate_dir.is_dir() or affiliate_dir.name.startswith("."):
            continue
        if period_re.match(affiliate_dir.name):
            continue
        for workplace_dir in affiliate_dir.iterdir():
            if not workplace_dir.is_dir():
                continue
            if (workplace_dir / period).is_dir():
                ensure_scope_manifest(PayrollScope(affiliate_dir.name, workplace_dir.name, period))


def payroll_file_path(scope: PayrollScope, filename: str) -> Path | None:
    path = resolve_output_dir(scope) / filename
    return path if path.is_file() else None


def invoice_file_path(scope: PayrollScope) -> Path | None:
    out_dir = resolve_output_dir(scope)
    manifest = load_scope_manifest(scope)
    name = str(manifest.get("invoice_file") or "").strip()
    if name:
        path = out_dir / name
        if path.is_file():
            return path
    for candidate in (INVOICE_STORED_NAME, "청구서.xlsx"):
        path = out_dir / candidate
        if path.is_file():
            return path
    return None
