"""
services/ai_agent_actions.py - Personal AI Agent 업무 액션 (보고·자료 탐색·차트)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from core.session_service import UserSession, require_session
from services.ai_report_assets import ReportDraftBundle, build_report_draft
from services.ai_resource_search import ResourceSearchResult, search_platform_resources

_REPORT_KW = (
    "보고",
    "기안",
    "초안",
    "임원",
    "경영",
    "요약보고",
    "월별보고",
    "보고서",
    "draft",
    "report",
)
_SEARCH_KW = (
    "찾아",
    "검색",
    "어디",
    "자료",
    "양식",
    "파일",
    "엑셀",
    "첨부",
    "문서",
)


@dataclass
class AgentActionResult:
    resource_context: str = ""
    report_context: str = ""
    attachment_paths: list[Path] = field(default_factory=list)
    summary_lines: list[str] = field(default_factory=list)
    report_bundle: ReportDraftBundle | None = None
    search_result: ResourceSearchResult | None = None

    @property
    def changed(self) -> bool:
        return bool(self.summary_lines or self.attachment_paths)

    @property
    def context_appendix(self) -> str:
        parts: list[str] = []
        if self.summary_lines:
            parts.append("[실행된 AI 업무 작업]\n" + "\n".join(f"✅ {m}" for m in self.summary_lines))
        if self.report_context:
            parts.append(self.report_context)
        if self.resource_context:
            parts.append(self.resource_context)
        return "\n\n".join(parts)


def _wants_report(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in _REPORT_KW)


def _wants_resource_search(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in _SEARCH_KW) or bool(re.search(r"\d{4}[-/년]\s*\d{1,2}", t))


def try_handle_agent_actions(
    question: str,
    session: UserSession | None = None,
) -> AgentActionResult:
    """보고 초안·플랫폼 자료 탐색·차트 생성."""
    sess = session or require_session()
    text = str(question or "").strip()
    result = AgentActionResult()

    if not text:
        return result

    if _wants_resource_search(text) or _wants_report(text):
        search = search_platform_resources(text, sess)
        result.search_result = search
        result.resource_context = search.format_context()

    if _wants_report(text):
        bundle = build_report_draft(text, sess, export_excel=True, render_charts=True)
        if bundle:
            result.report_bundle = bundle
            result.report_context = bundle.format_context()
            result.summary_lines.append(
                f"{bundle.period_label} 보고 초안·집계를 준비했습니다."
            )
            if bundle.excel_path and bundle.excel_path.is_file():
                result.attachment_paths.append(bundle.excel_path)
                result.summary_lines.append(f"Excel 저장: {bundle.excel_path.name}")
            for chart in bundle.chart_paths:
                if chart.is_file():
                    result.attachment_paths.append(chart)
            if bundle.chart_paths:
                result.summary_lines.append(f"차트 이미지 {len(bundle.chart_paths)}개 생성")

    elif _wants_resource_search(text) and result.search_result and result.search_result.resources:
        top = result.search_result.resources[0]
        result.summary_lines.append(f"관련 자료 {len(result.search_result.resources)}건을 찾았습니다. (대표: {top.label})")

    return result
