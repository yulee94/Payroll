"""
services/ui_performance.py - Tkinter dashboard startup/perceived-lag optimizations.

The main dashboard currently owns many heavy panels. Building all of them during
startup makes the first window feel slow even when the user only needs login or
payroll upload. This module installs a conservative lazy-loading patch: page
frames are created at startup, but expensive page contents are built only when
that page is first opened.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

_PAGE_BUILDERS: dict[str, str] = {
    "front": "_build_front_page",
    "login": "_build_login_page",
    "launcher": "_build_launcher_page",
    "tenant": "_build_tenant_page",
    "permissions": "_build_permissions_page",
    "org": "_build_org_page",
    "group_settings": "_build_group_settings_page",
    "home": "_build_home_page",
    "archive": "_build_archive_page",
    "summary": "_build_summary_page",
    "monthly_report": "_build_monthly_report_page",
    "reports": "_build_reports_page",
    "settings": "_build_settings_page",
    "workflow": "_build_workflow_page",
    "hr": "_build_hr_page",
    "recruitment": "_build_recruitment_page",
    "kpi": "_build_kpi_page",
    "maintenance": "_build_maintenance_page",
    "bidding": "_build_bidding_page",
    "accounting": "_build_accounting_page",
}


def page_builder_map() -> dict[str, str]:
    """Return a copy for tests and diagnostics."""
    return dict(_PAGE_BUILDERS)


def _noop_builder(self: Any, *_args: Any, **_kwargs: Any) -> None:
    return None


def _set_wait_cursor(widget: Any, enabled: bool) -> None:
    try:
        widget.configure(cursor="watch" if enabled else "")
        widget.update_idletasks()
    except Exception:
        pass


def install_dashboard_performance_patches(dashboard_cls: type) -> None:
    """
    Patch PayrollDashboard once.

    The patch is intentionally small and reversible by process restart. It does
    not change payroll calculations; it only changes when page widgets are built.
    """
    if getattr(dashboard_cls, "_bitween_perf_patched", False):
        return

    original_build_layout: Callable[..., Any] = dashboard_cls._build_layout
    original_show_page: Callable[..., Any] = dashboard_cls.show_page

    def _build_layout_lazy(self: Any, *args: Any, **kwargs: Any) -> Any:
        self._lazy_built_pages = set()
        self._lazy_building_pages = set()
        cls = type(self)
        saved_builders: dict[str, Any] = {}
        for method_name in set(_PAGE_BUILDERS.values()):
            if hasattr(cls, method_name):
                saved_builders[method_name] = getattr(cls, method_name)
                setattr(cls, method_name, _noop_builder)
        try:
            return original_build_layout(self, *args, **kwargs)
        finally:
            for method_name, method in saved_builders.items():
                setattr(cls, method_name, method)

    def _ensure_page_built(self: Any, page: str) -> None:
        pages = getattr(self, "pages", {})
        if page not in pages:
            return
        built: set[str] | None = getattr(self, "_lazy_built_pages", None)
        if built is None or page in built:
            return
        method_name = _PAGE_BUILDERS.get(page)
        if not method_name:
            return
        building: set[str] = getattr(self, "_lazy_building_pages", set())
        if page in building:
            return
        builder = getattr(self, method_name, None)
        if builder is None:
            return

        building.add(page)
        self._lazy_building_pages = building
        _set_wait_cursor(self, True)
        try:
            builder()
            built.add(page)
            self._lazy_built_pages = built
        finally:
            building.discard(page)
            _set_wait_cursor(self, False)

    def _show_page_lazy(self: Any, page: str) -> Any:
        try:
            target_page = self._coerce_page_for_session(page)
        except Exception:
            target_page = page
        _ensure_page_built(self, target_page)
        return original_show_page(self, page)

    dashboard_cls._build_layout = _build_layout_lazy
    dashboard_cls._ensure_page_built = _ensure_page_built
    dashboard_cls.show_page = _show_page_lazy
    dashboard_cls._bitween_perf_patched = True
