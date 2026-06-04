"""
payroll_settings_ui_bridge.py - enrich the payroll settings panel at runtime.

The settings panel already owns the payroll calculation form. This bridge adds
customer-facing payroll automation policy controls and the setup checklist
without replacing the existing settings UI.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
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


def _ensure_operation_policy_vars(panel: Any) -> None:
    if getattr(panel, "_bitween_operation_policy_vars_ready", False):
        return
    from services.payroll_policy_store import (
        INPUT_HYBRID,
        INPUT_LABELS,
        MISSING_CLOCK_LABELS,
        MISSING_CLOCK_WARN,
    )

    panel._op_input_label_to_key = {label: key for key, label in INPUT_LABELS.items()}
    panel._op_missing_label_to_key = {label: key for key, label in MISSING_CLOCK_LABELS.items()}
    panel._op_input_var = tk.StringVar(master=panel, value=INPUT_LABELS[INPUT_HYBRID])
    panel._op_payday_var = tk.StringVar(master=panel, value="25일")
    panel._op_attendance_enabled_var = tk.BooleanVar(master=panel, value=True)
    panel._op_attendance_source_var = tk.StringVar(master=panel, value="biometric")
    panel._op_rounding_var = tk.StringVar(master=panel, value="1")
    panel._op_late_grace_var = tk.StringVar(master=panel, value="0")
    panel._op_early_leave_grace_var = tk.StringVar(master=panel, value="0")
    panel._op_overtime_rounding_var = tk.StringVar(master=panel, value="1")
    panel._op_missing_clock_var = tk.StringVar(
        master=panel, value=MISSING_CLOCK_LABELS[MISSING_CLOCK_WARN]
    )
    panel._op_holiday_source_var = tk.StringVar(master=panel, value="invoice")
    panel._op_show_guide_var = tk.BooleanVar(master=panel, value=True)
    panel._op_note_var = tk.StringVar(master=panel, value="")
    panel._op_source_var = tk.StringVar(master=panel, value="")
    panel._bitween_operation_policy_vars_ready = True


def _add_operation_policy_controls(panel: Any) -> None:
    existing = getattr(panel, "_operation_policy_box", None)
    try:
        if existing is not None and existing.winfo_exists():
            return
    except Exception:
        pass

    breakdown_text = getattr(panel, "_breakdown_text", None)
    if breakdown_text is None:
        return
    breakdown_wrap = getattr(breakdown_text, "master", None)
    breakdown_box = getattr(breakdown_wrap, "master", None)
    pad = getattr(breakdown_box, "master", None)
    if pad is None:
        return

    from services.payroll_policy_store import INPUT_LABELS, MISSING_CLOCK_LABELS

    _ensure_operation_policy_vars(panel)
    box = ttk.LabelFrame(pad, text="급여 자동화 운영 기준", padding=12)
    try:
        box.pack(fill=tk.X, anchor=tk.W, pady=(12, 0), before=breakdown_box)
    except Exception:
        box.pack(fill=tk.X, anchor=tk.W, pady=(12, 0))
    panel._operation_policy_box = box

    ttk.Label(box, textvariable=panel._op_source_var, foreground="#666").pack(
        anchor=tk.W, pady=(0, 8)
    )

    row1 = ttk.Frame(box)
    row1.pack(fill=tk.X, pady=(0, 6))
    ttk.Label(row1, text="입력 방식", width=10).pack(side=tk.LEFT)
    ttk.Combobox(
        row1,
        textvariable=panel._op_input_var,
        values=list(INPUT_LABELS.values()),
        state="readonly",
        width=22,
    ).pack(side=tk.LEFT, padx=(0, 12))
    ttk.Label(row1, text="지급일").pack(side=tk.LEFT)
    ttk.Entry(row1, textvariable=panel._op_payday_var, width=10).pack(
        side=tk.LEFT, padx=(6, 12)
    )
    ttk.Checkbutton(
        row1,
        text="설정 안내 표시",
        variable=panel._op_show_guide_var,
    ).pack(side=tk.LEFT)

    row2 = ttk.Frame(box)
    row2.pack(fill=tk.X, pady=(0, 6))
    ttk.Checkbutton(
        row2,
        text="지문근태 사용",
        variable=panel._op_attendance_enabled_var,
    ).pack(side=tk.LEFT)
    ttk.Label(row2, text="출처").pack(side=tk.LEFT, padx=(14, 4))
    ttk.Entry(row2, textvariable=panel._op_attendance_source_var, width=12).pack(
        side=tk.LEFT, padx=(0, 12)
    )
    ttk.Label(row2, text="누락 출퇴근").pack(side=tk.LEFT)
    ttk.Combobox(
        row2,
        textvariable=panel._op_missing_clock_var,
        values=list(MISSING_CLOCK_LABELS.values()),
        state="readonly",
        width=14,
    ).pack(side=tk.LEFT, padx=(6, 0))

    row3 = ttk.Frame(box)
    row3.pack(fill=tk.X, pady=(0, 6))
    for label, var in (
        ("반올림", panel._op_rounding_var),
        ("지각 유예", panel._op_late_grace_var),
        ("조퇴 유예", panel._op_early_leave_grace_var),
        ("연장 반올림", panel._op_overtime_rounding_var),
    ):
        ttk.Label(row3, text=label).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Entry(row3, textvariable=var, width=5).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Label(row3, text="분").pack(side=tk.LEFT, padx=(0, 12))

    row4 = ttk.Frame(box)
    row4.pack(fill=tk.X, pady=(0, 8))
    ttk.Label(row4, text="메모", width=10).pack(side=tk.LEFT)
    ttk.Entry(row4, textvariable=panel._op_note_var, width=56).pack(
        side=tk.LEFT, fill=tk.X, expand=True
    )

    btn_row = ttk.Frame(box)
    btn_row.pack(fill=tk.X)
    ttk.Button(
        btn_row,
        text="운영 기준 저장",
        command=lambda p=panel: _save_operation_policy(p),
    ).pack(side=tk.LEFT, padx=(0, 8))
    panel._op_clear_button = ttk.Button(
        btn_row,
        text="사업장 기준 삭제",
        command=lambda p=panel: _clear_site_operation_policy(p),
    )
    panel._op_clear_button.pack(side=tk.LEFT)


def _current_operation_scope(panel: Any) -> tuple[str, str | None]:
    workplace = "" if panel._is_tenant_scope() else panel._selected_workplace()
    return workplace, panel._tenant_id()


def _load_operation_policy_form(panel: Any) -> None:
    if not getattr(panel, "_bitween_operation_policy_vars_ready", False):
        return
    from services.payroll_policy_store import (
        INPUT_LABELS,
        MISSING_CLOCK_LABELS,
        operation_policy_source_label,
        resolve_payroll_operation_policy,
    )

    workplace, tenant_id = _current_operation_scope(panel)
    resolved = resolve_payroll_operation_policy(workplace, tenant_id=tenant_id)
    policy = resolved["policy"]
    attendance = policy["attendance"]

    panel._op_input_var.set(INPUT_LABELS.get(policy["input_basis"], policy["input_basis"]))
    panel._op_payday_var.set(str(policy.get("payday") or "25일"))
    panel._op_show_guide_var.set(bool(policy.get("show_setup_guide", True)))
    panel._op_note_var.set(str(policy.get("policy_note") or ""))
    panel._op_attendance_enabled_var.set(bool(attendance.get("enabled")))
    panel._op_attendance_source_var.set(str(attendance.get("source") or "biometric"))
    panel._op_rounding_var.set(str(attendance.get("rounding_minutes", 1)))
    panel._op_late_grace_var.set(str(attendance.get("late_grace_minutes", 0)))
    panel._op_early_leave_grace_var.set(str(attendance.get("early_leave_grace_minutes", 0)))
    panel._op_overtime_rounding_var.set(str(attendance.get("overtime_rounding_minutes", 1)))
    panel._op_missing_clock_var.set(
        MISSING_CLOCK_LABELS.get(
            attendance.get("missing_clock_policy"), attendance.get("missing_clock_policy", "warn")
        )
    )
    panel._op_holiday_source_var.set(str(attendance.get("holiday_source") or "invoice"))

    target = "법인 기본" if panel._is_tenant_scope() else f"사업장: {workplace}"
    panel._op_source_var.set(
        f"{target} · 적용 기준: {operation_policy_source_label(resolved['source'])}"
    )
    clear_btn = getattr(panel, "_op_clear_button", None)
    if clear_btn is not None:
        clear_btn.configure(state=tk.DISABLED if panel._is_tenant_scope() else tk.NORMAL)


def _parse_minutes(value: str, field_name: str, *, minimum: int = 0, maximum: int = 1440) -> int:
    raw = str(value or "").strip().replace(",", "")
    try:
        parsed = int(float(raw))
    except ValueError:
        raise ValueError(f"{field_name}은 숫자로 입력해 주세요.") from None
    if parsed < minimum or parsed > maximum:
        raise ValueError(f"{field_name}은 {minimum}~{maximum} 사이여야 합니다.")
    return parsed


def _operation_policy_from_panel(panel: Any) -> dict[str, Any]:
    from services.payroll_policy_store import (
        INPUT_CHOICES,
        INPUT_HYBRID,
        MISSING_CLOCK_POLICIES,
        MISSING_CLOCK_WARN,
    )

    input_basis = panel._op_input_label_to_key.get(panel._op_input_var.get(), panel._op_input_var.get())
    if input_basis not in INPUT_CHOICES:
        input_basis = INPUT_HYBRID
    missing_clock_policy = panel._op_missing_label_to_key.get(
        panel._op_missing_clock_var.get(), panel._op_missing_clock_var.get()
    )
    if missing_clock_policy not in MISSING_CLOCK_POLICIES:
        missing_clock_policy = MISSING_CLOCK_WARN

    return {
        "input_basis": input_basis,
        "payday": str(panel._op_payday_var.get() or "25일").strip() or "25일",
        "show_setup_guide": bool(panel._op_show_guide_var.get()),
        "policy_note": str(panel._op_note_var.get() or "").strip(),
        "attendance": {
            "enabled": bool(panel._op_attendance_enabled_var.get()),
            "source": str(panel._op_attendance_source_var.get() or "biometric").strip()
            or "biometric",
            "rounding_minutes": _parse_minutes(
                panel._op_rounding_var.get(), "반올림", minimum=1, maximum=60
            ),
            "late_grace_minutes": _parse_minutes(
                panel._op_late_grace_var.get(), "지각 유예", minimum=0, maximum=240
            ),
            "early_leave_grace_minutes": _parse_minutes(
                panel._op_early_leave_grace_var.get(), "조퇴 유예", minimum=0, maximum=240
            ),
            "overtime_rounding_minutes": _parse_minutes(
                panel._op_overtime_rounding_var.get(), "연장 반올림", minimum=1, maximum=60
            ),
            "missing_clock_policy": missing_clock_policy,
            "holiday_source": str(panel._op_holiday_source_var.get() or "invoice").strip()
            or "invoice",
        },
    }


def _save_operation_policy(panel: Any) -> None:
    from services.payroll_policy_store import (
        save_site_payroll_operation_policy,
        save_tenant_payroll_operation_policy,
    )

    try:
        policy = _operation_policy_from_panel(panel)
    except ValueError as exc:
        messagebox.showerror("입력 오류", str(exc), parent=panel.winfo_toplevel())
        return

    workplace, tenant_id = _current_operation_scope(panel)
    try:
        if panel._is_tenant_scope():
            save_tenant_payroll_operation_policy(policy, tenant_id=tenant_id)
            panel._status_var.set("법인 기본 운영 기준 저장됨")
        else:
            save_site_payroll_operation_policy(workplace, policy, tenant_id=tenant_id)
            panel._status_var.set(f"사업장: {workplace} 운영 기준 저장됨")
    except ValueError as exc:
        messagebox.showerror("저장 실패", str(exc), parent=panel.winfo_toplevel())
        return

    _load_operation_policy_form(panel)
    panel._refresh_breakdown_panel()


def _clear_site_operation_policy(panel: Any) -> None:
    from services.payroll_policy_store import clear_site_payroll_operation_policy

    if panel._is_tenant_scope():
        messagebox.showinfo(
            "안내",
            "법인 기본을 편집 중입니다. 사업장을 선택한 뒤 개별 운영 기준을 삭제할 수 있습니다.",
            parent=panel.winfo_toplevel(),
        )
        return
    workplace, tenant_id = _current_operation_scope(panel)
    if not messagebox.askyesno(
        "확인",
        f"「{workplace}」 사업장 운영 기준을 삭제하고 법인 기본을 사용할까요?",
        parent=panel.winfo_toplevel(),
    ):
        return
    clear_site_payroll_operation_policy(workplace, tenant_id=tenant_id)
    panel._status_var.set(f"사업장: {workplace} 운영 기준 삭제됨")
    _load_operation_policy_form(panel)
    panel._refresh_breakdown_panel()


def install_payroll_settings_panel_integrations(settings_module: Any) -> None:
    """Patch PayrollSettingsPanel once to show operation policy controls and setup guide."""
    panel_cls = getattr(settings_module, "PayrollSettingsPanel", None)
    if panel_cls is None:
        return

    if not getattr(panel_cls, "_bitween_operation_policy_patched", False):
        if hasattr(panel_cls, "_build"):
            original_build: Callable[..., Any] = panel_cls._build

            def _build_with_operation_policy(self: Any, *args: Any, **kwargs: Any) -> Any:
                result = original_build(self, *args, **kwargs)
                try:
                    _add_operation_policy_controls(self)
                    _load_operation_policy_form(self)
                except Exception:
                    pass
                return result

            panel_cls._build = _build_with_operation_policy

        if hasattr(panel_cls, "_load_scope_form"):
            original_load_scope: Callable[..., Any] = panel_cls._load_scope_form

            def _load_scope_form_with_operation_policy(self: Any, *args: Any, **kwargs: Any) -> Any:
                result = original_load_scope(self, *args, **kwargs)
                try:
                    _load_operation_policy_form(self)
                except Exception:
                    pass
                return result

            panel_cls._load_scope_form = _load_scope_form_with_operation_policy

        panel_cls._bitween_operation_policy_patched = True

    if hasattr(panel_cls, "_refresh_breakdown_panel") and not getattr(
        panel_cls, "_bitween_setup_guide_patched", False
    ):
        original_refresh: Callable[..., Any] = panel_cls._refresh_breakdown_panel

        def _refresh_breakdown_panel_with_setup_guide(
            self: Any, *args: Any, **kwargs: Any
        ) -> Any:
            result = original_refresh(self, *args, **kwargs)
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
