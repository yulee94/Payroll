"""
services/ai_report_assets.py - 보고 초안·차트(그래프) 생성 (Personal AI용)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from core.access_control import (
    build_month_summary_secured,
    can_view_executive_reports,
    load_payroll_records_secured,
    session_role,
)
from core.config import MONTHLY_REPORTS_DIR
from core.paths import app_data_dir
from core.session_service import UserSession, require_session
from core.tenant_data_scope import list_periods_for_tenant
from payroll_archive import format_period_display
from services.executive_analytics import build_executive_analytics
from services.monthly_report import (
    build_report_bundle,
    export_monthly_report_excel,
    get_or_create_report_path,
)
from services.payroll_ai_context import parse_period_from_text
from services.ai_safety_policy import assert_ai_write_allowed


@dataclass
class ReportDraftBundle:
    period: str
    period_label: str
    draft_text: str
    analytics_summary: str = ""
    excel_path: Path | None = None
    chart_paths: list[Path] = field(default_factory=list)

    def format_context(self) -> str:
        lines = [
            f"=== 보고 초안 ({self.period_label}) ===",
            "아래 수치·문단만 보고서·기안서 근거로 사용하세요.",
            "",
            self.draft_text[:8000],
        ]
        if self.analytics_summary:
            lines.extend(["", "■ 집계·추이 요약", self.analytics_summary[:4000]])
        if self.excel_path and self.excel_path.is_file():
            lines.append(f"\n[저장된 Excel] {self.excel_path}")
        if self.chart_paths:
            lines.append("[생성된 차트 이미지]")
            for p in self.chart_paths:
                lines.append(f"  · {p.name}: {p}")
        return "\n".join(lines)


def _ai_assets_dir(sess: UserSession) -> Path:
    d = (
        app_data_dir()
        / "workspace"
        / sess.tenant_id
        / "users"
        / sess.user_id
        / "ai_assets"
    )
    d.mkdir(parents=True, exist_ok=True)
    return d


def render_executive_charts(
    period: str,
    session: UserSession | None = None,
) -> list[Path]:
    """임원용 KPI 차트 PNG 생성 (matplotlib)."""
    sess = session or require_session()
    if not can_view_executive_reports(session_role(sess)):
        return []

    records = load_payroll_records_secured(period, sess.tenant_id, session=sess)
    if not records:
        return []

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return []

    analytics = build_executive_analytics(period, summary=build_month_summary_secured(period, sess.tenant_id, session=sess), records=records)
    out_dir = _ai_assets_dir(sess)
    assert_ai_write_allowed(out_dir, sess)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    paths: list[Path] = []

    sites = analytics.sites[:8]
    if sites:
        fig, ax = plt.subplots(figsize=(8, max(3, len(sites) * 0.45)), dpi=120)
        names = [s.name for s in sites]
        gross = [s.gross / 1_000_000 for s in sites]
        ax.barh(names, gross, color="#1F3864")
        ax.set_xlabel("총지급 (백만원)")
        ax.set_title(f"{analytics.period_label} 사업장별 총지급")
        fig.tight_layout()
        p = out_dir / f"chart_site_gross_{period}_{stamp}.png"
        assert_ai_write_allowed(p, sess)
        fig.savefig(p, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        paths.append(p)

    if analytics.ytd_months:
        fig, ax = plt.subplots(figsize=(8, 4), dpi=120)
        labels = [pt.label for pt in analytics.ytd_months]
        vals = [pt.gross / 1_000_000 for pt in analytics.ytd_months]
        ax.plot(labels, vals, marker="o", color="#2563EB")
        ax.set_ylabel("총지급 (백만원)")
        ax.set_title(f"{analytics.ytd_label or '연간'} 총급여 추이")
        plt.xticks(rotation=35, ha="right")
        fig.tight_layout()
        p = out_dir / f"chart_ytd_gross_{period}_{stamp}.png"
        assert_ai_write_allowed(p, sess)
        fig.savefig(p, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        paths.append(p)

    return paths


def build_analytics_text(period: str, session: UserSession) -> str:
    records = load_payroll_records_secured(period, session.tenant_id, session=session)
    if not records:
        return ""
    a = build_executive_analytics(
        period,
        summary=build_month_summary_secured(period, session.tenant_id, session=session),
        records=records,
    )
    lines = [
        f"인원 {a.summary.employee_count}명 (전월 대비 {a.headcount_delta:+d}명)",
        f"총지급 {a.summary.total_gross:,}원 (전월 대비 {a.gross_delta:+,}원)",
        f"연장수당 합계 {a.ot_total:,}원",
    ]
    if a.sites:
        lines.append("사업장별 상위:")
        for s in a.sites[:5]:
            lines.append(f"  · {s.name}: {s.headcount}명 / {s.gross:,}원")
    return "\n".join(lines)


def build_report_draft(
    question: str,
    session: UserSession | None = None,
    *,
    export_excel: bool = True,
    render_charts: bool = True,
) -> ReportDraftBundle | None:
    """월별 보고·기안용 초안 텍스트 + 선택적 Excel·차트."""
    sess = session or require_session()
    tid = sess.tenant_id
    periods = list_periods_for_tenant(tid)
    period = parse_period_from_text(question, periods)
    if not period and periods:
        period = periods[0]
    if not period:
        return None

    summary = build_month_summary_secured(period, tid, session=sess)
    if not summary.has_output:
        return None

    draft_text, records = build_report_bundle(period, summary)
    analytics_summary = build_analytics_text(period, sess)

    excel_path: Path | None = None
    if export_excel and can_view_executive_reports(session_role(sess)):
        reports_dir = MONTHLY_REPORTS_DIR
        reports_dir.mkdir(parents=True, exist_ok=True)
        excel_path = get_or_create_report_path(period, reports_dir)
        try:
            excel_path.parent.mkdir(parents=True, exist_ok=True)
            assert_ai_write_allowed(excel_path, sess)
            export_monthly_report_excel(period, summary, records, excel_path)
        except (PermissionError, OSError, Exception):
            if excel_path is None or not excel_path.is_file():
                excel_path = None

    chart_paths: list[Path] = []
    if render_charts:
        chart_paths = render_executive_charts(period, sess)

    return ReportDraftBundle(
        period=period,
        period_label=format_period_display(period),
        draft_text=draft_text,
        analytics_summary=analytics_summary,
        excel_path=excel_path,
        chart_paths=chart_paths,
    )
