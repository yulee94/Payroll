"""
services/payroll_scope.py - 계열사·사업장·급여월별 출력 경로
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from excel_writer import OUTPUT_DIR
from payroll_archive import format_period_display
from payroll_comparison import prev_period_label

_SCOPE_SEP = "\x1f"
_PERIOD_RE = re.compile(r"^\d{4}-\d{2}$")
_INVALID_PATH = re.compile(r'[<>:"/\\|?*]')


@dataclass(frozen=True)
class PayrollScope:
    affiliate: str
    workplace: str
    period: str

    @property
    def key(self) -> str:
        return f"{self.affiliate}{_SCOPE_SEP}{self.workplace}{_SCOPE_SEP}{self.period}"

    def display_label(self) -> str:
        return f"{format_period_display(self.period)} · {self.workplace} · {self.affiliate}"

    def breadcrumb(self) -> str:
        from core.brand_display import company_name_line

        return f"{company_name_line()}  >  {self.affiliate}  >  {self.workplace}  >  {format_period_display(self.period)}"

    def output_dir(self) -> Path:
        return OUTPUT_DIR / _safe_path(self.affiliate) / _safe_path(self.workplace) / self.period

    def prior(self) -> PayrollScope:
        return PayrollScope(self.affiliate, self.workplace, prev_period_label(self.period))

    @staticmethod
    def from_key(key: str) -> PayrollScope | None:
        if not key or _SCOPE_SEP not in key:
            return None
        parts = key.split(_SCOPE_SEP, 2)
        if len(parts) != 3:
            return None
        return PayrollScope(parts[0], parts[1], parts[2])

    @staticmethod
    def try_parse_key(key: str) -> PayrollScope | None:
        scope = PayrollScope.from_key(key)
        if scope:
            return scope
        if _PERIOD_RE.match(key):
            from services.archive_storage import infer_period_manifest

            m = infer_period_manifest(key)
            return PayrollScope(
                str(m.get("affiliate") or ""),
                str(m.get("workplace") or ""),
                key,
            )
        return None


def _safe_path(name: str) -> str:
    s = (name or "미분류").strip()
    s = _INVALID_PATH.sub("_", s)
    return s or "미분류"


def resolve_output_dir(scope: PayrollScope) -> Path:
    """신규(중첩) 또는 구(평면) output 경로를 반환."""
    nested = scope.output_dir()
    legacy = OUTPUT_DIR / scope.period
    if nested.is_dir() and _dir_has_payroll(nested):
        return nested
    if legacy.is_dir() and _dir_has_payroll(legacy):
        return legacy
    return nested


def _dir_has_payroll(path: Path) -> bool:
    from services.archive_storage import PAYROLL_OUTPUT_NAMES

    return any((path / name).is_file() for name in PAYROLL_OUTPUT_NAMES)


def discover_scopes() -> list[PayrollScope]:
    """output/ 아래 모든 계열사·사업장·월 조합."""
    if not OUTPUT_DIR.exists():
        return []
    found: dict[str, PayrollScope] = {}

    for level1 in OUTPUT_DIR.iterdir():
        if not level1.is_dir() or level1.name.startswith("."):
            continue
        if _PERIOD_RE.match(level1.name):
            scope = _scope_from_dir(level1)
            found[scope.key] = scope
            continue
        for level2 in level1.iterdir():
            if not level2.is_dir():
                continue
            for level3 in level2.iterdir():
                if not level3.is_dir() or not _PERIOD_RE.match(level3.name):
                    continue
                scope = _scope_from_dir(level3, affiliate=level1.name, workplace=level2.name)
                found[scope.key] = scope

    scopes = list(found.values())
    scopes.sort(key=lambda s: (s.period, s.affiliate, s.workplace), reverse=True)
    return scopes


def _scope_from_dir(
    period_dir: Path,
    affiliate: str = "",
    workplace: str = "",
) -> PayrollScope:
    period = period_dir.name
    manifest: dict = {}

    manifest_path = period_dir / "payroll_manifest.json"
    if manifest_path.is_file():
        try:
            import json

            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                manifest = data
        except (OSError, ValueError):
            pass

    aff = str(manifest.get("affiliate") or affiliate or "").strip()
    wp = str(manifest.get("workplace") or workplace or "").strip()

    if (not aff or not wp) and period_dir.resolve() == (OUTPUT_DIR / period).resolve():
        from services.archive_storage import infer_scope_manifest

        inferred = infer_scope_manifest(PayrollScope(aff or affiliate or "", wp or workplace or "", period))
        aff = aff or str(inferred.get("affiliate") or "").strip()
        wp = wp or str(inferred.get("workplace") or "").strip()

    if not aff:
        from core.org_config import get_default_affiliate

        aff = get_default_affiliate()
    if not wp:
        wp = "미분류"
    return PayrollScope(aff, wp, period)


def list_scope_keys() -> list[str]:
    return [s.key for s in discover_scopes()]
