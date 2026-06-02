"""
services/ai_resource_search.py - 플랫폼 양식·보고서·자료함 자동 탐색
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.access_control import session_role
from core.config import MONTHLY_REPORTS_DIR
from core.labels import label_for_filename
from core.paths import app_data_dir, app_install_dir
from core.session_service import UserSession, require_session
from core.tenant_data_scope import list_periods_for_tenant
from excel_writer import OUTPUT_DIR, TEMPLATES_DIR
from payroll_archive import format_period_display
from payroll_builder import get_templates_roster_path
from services.payroll_ai_context import parse_period_from_text
from services.payroll_scope import discover_scopes, resolve_output_dir

_IMAGE_EXT = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"})
_VIDEO_EXT = frozenset({".mp4", ".webm", ".mov", ".avi", ".mkv"})
_DOC_EXT = frozenset({".xlsx", ".xls", ".csv", ".pdf", ".docx", ".doc", ".json", ".txt", ".md"})


@dataclass
class PlatformResource:
    kind: str  # template | report | payroll | invoice | roster | image | video | other
    label: str
    path: Path
    period: str = ""
    workplace: str = ""
    affiliate: str = ""
    score: float = 0.0


@dataclass
class ResourceSearchResult:
    query: str
    resources: list[PlatformResource] = field(default_factory=list)

    def format_context(self, *, limit: int = 12) -> str:
        if not self.resources:
            return "=== 플랫폼 자료·양식 ===\n(검색 조건에 맞는 파일이 없습니다.)"
        lines = [
            "=== 플랫폼 자료·양식 (자동 탐색) ===",
            "아래 경로·파일만 실제 존재하는 자료입니다. 기안·보고 시 참고하세요.",
        ]
        for r in self.resources[:limit]:
            meta = []
            if r.period:
                meta.append(format_period_display(r.period))
            if r.workplace:
                meta.append(r.workplace)
            meta_s = f" ({', '.join(meta)})" if meta else ""
            lines.append(f"  · [{r.kind}] {r.label}{meta_s}\n    경로: {r.path}")
        return "\n".join(lines)


def _tokenize_query(q: str) -> list[str]:
    t = re.sub(r"[^\w가-힣]+", " ", str(q or "").lower())
    return [w for w in t.split() if len(w) >= 2]


def _score_text(name: str, tokens: list[str]) -> float:
    nl = name.lower()
    if not tokens:
        return 0.0
    hits = sum(1 for tok in tokens if tok in nl)
    return hits / len(tokens)


def _kind_for_path(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in _IMAGE_EXT:
        return "image"
    if ext in _VIDEO_EXT:
        return "video"
    name = path.name
    if "도급비" in name or "청구" in name:
        return "invoice"
    if "명부" in name:
        return "roster"
    if "월별요약" in name or "보고" in name:
        return "report"
    if "양식" in str(path.parent) or path.parent.name == "templates":
        return "template"
    if ext in (".xlsx", ".xls"):
        return "payroll"
    return "other"


def _iter_template_resources() -> list[PlatformResource]:
    out: list[PlatformResource] = []
    for name in (
        "급여대장양식.xlsx",
        "급여명세서양식.xlsx",
        "지급내역양식.xlsx",
    ):
        p = TEMPLATES_DIR / name
        if p.is_file():
            out.append(
                PlatformResource(
                    kind="template",
                    label=label_for_filename(name) + " 양식",
                    path=p,
                )
            )
    roster = get_templates_roster_path()
    if roster and roster.is_file():
        out.append(
            PlatformResource(
                kind="template",
                label="근로자 명부 양식",
                path=roster,
            )
        )
    return out


def _iter_monthly_reports(tenant_id: str) -> list[PlatformResource]:
    out: list[PlatformResource] = []
    for base in (MONTHLY_REPORTS_DIR, app_data_dir() / "월별보고"):
        if not base.is_dir():
            continue
        for p in sorted(base.glob("*_월별요약보고.xlsx"), reverse=True):
            period = p.name.replace("_월별요약보고.xlsx", "")[:7]
            out.append(
                PlatformResource(
                    kind="report",
                    label="월별 요약 보고",
                    path=p,
                    period=period,
                )
            )
    return out


def _iter_scope_outputs(tenant_id: str, period_hint: str | None) -> list[PlatformResource]:
    out: list[PlatformResource] = []
    periods = list_periods_for_tenant(tenant_id)
    target_periods = [period_hint] if period_hint and period_hint in periods else periods[:6]

    for scope in discover_scopes():
        if scope.period not in target_periods and period_hint:
            continue
        out_dir = resolve_output_dir(scope)
        if not out_dir.is_dir():
            continue
        for p in sorted(out_dir.iterdir()):
            if not p.is_file():
                continue
            if p.suffix.lower() not in _DOC_EXT | _IMAGE_EXT | _VIDEO_EXT:
                continue
            out.append(
                PlatformResource(
                    kind=_kind_for_path(p),
                    label=label_for_filename(p.name),
                    path=p,
                    period=scope.period,
                    workplace=scope.workplace or "",
                    affiliate=scope.affiliate or "",
                )
            )
    return out


def _iter_assets_media() -> list[PlatformResource]:
    out: list[PlatformResource] = []
    assets = app_install_dir() / "assets"
    if not assets.is_dir():
        return out
    for p in assets.rglob("*"):
        if not p.is_file():
            continue
        ext = p.suffix.lower()
        if ext in _IMAGE_EXT | _VIDEO_EXT:
            out.append(
                PlatformResource(
                    kind=_kind_for_path(p),
                    label=p.stem,
                    path=p,
                )
            )
    return out


def search_platform_resources(
    query: str,
    session: UserSession | None = None,
    *,
    limit: int = 15,
) -> ResourceSearchResult:
    """질문 키워드·급여월로 플랫폼 내 양식·산출물·미디어 탐색."""
    sess = session or require_session()
    tid = sess.tenant_id
    tokens = _tokenize_query(query)
    periods = list_periods_for_tenant(tid)
    period_hint = parse_period_from_text(query, periods)

    candidates: list[PlatformResource] = []
    candidates.extend(_iter_template_resources())
    candidates.extend(_iter_monthly_reports(tid))
    candidates.extend(_iter_scope_outputs(tid, period_hint))
    candidates.extend(_iter_assets_media())

    report_kw = ("보고", "기안", "양식", "자료", "엑셀", "급여", "명세", "청구", "명부", "월별")
    if any(k in query for k in report_kw) or period_hint:
        for r in candidates:
            r.score = _score_text(r.label + " " + r.path.name, tokens)
            if period_hint and r.period == period_hint:
                r.score += 0.5
    else:
        for r in candidates:
            r.score = _score_text(r.label + " " + r.path.name, tokens) * 0.5

    ranked = sorted(candidates, key=lambda x: x.score, reverse=True)
    if tokens:
        ranked = [r for r in ranked if r.score > 0] or ranked[:8]
    else:
        ranked = ranked[:8]

    return ResourceSearchResult(query=query, resources=ranked[:limit])
