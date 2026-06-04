"""
payroll_ui_bridge.py - runtime bridge from the desktop UI to payroll backend services.

The existing Tkinter dashboard imports ``process_invoice`` directly. This bridge
lets the UI keep that call shape while routing the work through the API-ready
payroll automation service.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


def _active_tenant_id() -> str | None:
    try:
        from core.session_service import session_tenant_id

        return session_tenant_id()
    except Exception:
        return None


def process_invoice_via_automation(
    invoice_path: Path | str,
    scope: Any,
    interactive_parent: Any = None,
) -> dict[str, Any]:
    """Keep the UI's process_invoice contract while using the backend service."""
    from services.payroll_automation import run_invoice_payroll

    result = run_invoice_payroll(
        Path(invoice_path),
        scope,
        interactive_parent=interactive_parent,
        tenant_id=_active_tenant_id(),
    )
    if result.ok:
        return dict(result.raw or result.as_dict())
    if result.exception is not None:
        raise result.exception
    raise RuntimeError(result.error or "급여 산출에 실패했습니다.")


def _install_settings_panel_integrations() -> None:
    settings_module = sys.modules.get("ui.payroll_settings_panel")
    if settings_module is None:
        return
    try:
        from services.payroll_settings_ui_bridge import install_payroll_settings_panel_integrations

        install_payroll_settings_panel_integrations(settings_module)
    except Exception:
        pass


def install_app_ui_integrations(app_ui_module: Any) -> None:
    """Patch app_ui once after it is imported."""
    if getattr(app_ui_module, "_bitween_payroll_integrations_installed", False):
        return

    dashboard_cls = getattr(app_ui_module, "PayrollDashboard", None)
    if dashboard_cls is not None:
        try:
            from services.ui_performance import install_dashboard_performance_patches

            install_dashboard_performance_patches(dashboard_cls)
        except Exception:
            # Startup should never fail because a performance patch could not install.
            pass

    _install_settings_panel_integrations()

    if hasattr(app_ui_module, "process_invoice"):
        if not hasattr(app_ui_module, "_bitween_original_process_invoice"):
            app_ui_module._bitween_original_process_invoice = app_ui_module.process_invoice
        app_ui_module.process_invoice = process_invoice_via_automation

    app_ui_module._bitween_payroll_integrations_installed = True
