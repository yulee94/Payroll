"""
payroll_settings_ui_bridge.py - enrich the payroll settings panel at runtime.

The settings panel already has a calculation breakdown text area. This bridge
adds the customer-facing setup checklist from services.payroll_self_service
without replacing the existing settings UI.
"""

from __future__ import annotations

from typing import Any, Callable


def _append_setup_guide(panel: Any, guide: str) -> None:
    text = getattr(panel, "_breakdown_text", None)
    if text is None or not guide:
        return
    try:
        text.configure(state="normal")
        current = text.get("1.0", "end").strip()
        text.delete("1.0", "end")
        payload = f"{current}\n\n{guide}" if current else guide
        text.insert("1.0", payload)
        text.configure(state="disabled")
    except Exception:
        pass


def install_payroll_settings_panel_integrations(settings_module: Any) -> None:
    """Patch PayrollSettingsPanel once to show the setup checklist."""
    panel_cls = getattr(settings_module, "PayrollSettingsPanel", None)
    if panel_cls is None or getattr(panel_cls, "_bitween_setup_guide_patched", False):
        return

    original: Callable[..., Any] = panel_cls._refresh_breakdown_panel

    def _refresh_breakdown_panel_with_setup_guide(self: Any, *args: Any, **kwargs: Any) -> Any:
        result = original(self, *args, **kwargs)
        try:
            from services.payroll_self_service import format_payroll_setup_guide

            workplace = "" if self._is_tenant_scope() else self._selected_workplace()
            guide = format_payroll_setup_guide(workplace, tenant_id=self._tenant_id())
            _append_setup_guide(self, guide)
        except Exception:
            pass
        return result

    panel_cls._refresh_breakdown_panel = _refresh_breakdown_panel_with_setup_guide
    panel_cls._bitween_setup_guide_patched = True
