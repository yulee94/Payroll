"""Lightweight labels for generated Workspace source-linked items."""

from __future__ import annotations


def workspace_source_label(item: dict[str, object]) -> str:
    """Return a human label for generated workflow/calendar/To-Do source links."""
    source = str(item.get("source") or "")
    if source == "business_trip_overdue":
        return "출장 지연"
    if source == "workflow_execution":
        return "실행업무"
    if source == "workflow_approval":
        return "결재"
    if source == "workflow_cc":
        return "참조"
    if source == "workflow":
        return "전자결재"
    return ""
