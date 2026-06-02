"""
deficit_leave_dialog.py - 잔여연차 부족 시 유급연차·휴업(회사)·무급/결근 일수 분할
"""

from __future__ import annotations

import math
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

from annual_leave_manager import default_leave_split_for_case
from services.payroll_settings_store import (
    LEGAL_MIN_SHUTDOWN_PAY_PERCENT,
    get_shutdown_pay_percent,
)
from utils import safe_number


def _day_choices(max_days: float) -> list[str]:
    n = max(0, int(math.floor(max_days + 1e-9)))
    if max_days > n + 1e-9:
        vals: list[str] = []
        step = 0.5
        v = 0.0
        while v <= max_days + 1e-9:
            vals.append(str(int(v)) if v == int(v) else f"{v:g}")
            v += step
        return vals
    return [str(i) for i in range(n + 1)]


def _parse_days(text: str) -> float:
    return max(0.0, safe_number(str(text).strip().replace(",", ""), 0.0))


def _max_paid_days(case: dict[str, Any]) -> float:
    available = case.get("available")
    if available is None:
        return 0.0
    return max(0.0, float(available))


def show_deficit_leave_decision_dialog(
    parent: tk.Misc,
    cases: list[dict[str, Any]],
) -> dict[str, dict[str, float]] | None:
    """
    당월 연차 사용을 유급 연차 / 휴업(회사 사정) / 무급·결근으로 분할.

    Returns:
        {name_key: {"annual_days", "shutdown_days", "unpaid_days"}} 또는 None
    """
    if not cases:
        return {}

    pay_rate = get_shutdown_pay_percent()
    result: dict[str, dict[str, float]] | None = None
    row_state: list[dict[str, Any]] = []

    win = tk.Toplevel(parent)
    win.title("연차·휴업·무급/결근 일수 분할")
    win.transient(parent)
    win.grab_set()
    win.minsize(780, 380)

    outer = ttk.Frame(win, padding=12)
    outer.pack(fill=tk.BOTH, expand=True)

    ttk.Label(
        outer,
        text="당월 연차 사용 일수를 유급 연차 · 휴업(회사) · 무급/결근으로 나누어 주세요.",
        font=("맑은 고딕", 10, "bold"),
        justify=tk.LEFT,
    ).pack(anchor=tk.W, pady=(0, 4))

    ttk.Label(
        outer,
        text=(
            f"휴업(회사): 연차 없이 회사 사정 휴업 시 총급여의 {pay_rate:g}% 지급 "
            f"(법정 최저 {LEGAL_MIN_SHUTDOWN_PAY_PERCENT:g}%, 설정에서 변경 가능)\n"
            "※ 세 칸의 합계는 「당월 연차」와 같아야 합니다. 잔여 연차 0이면 유급 연차는 0일로 고정됩니다."
        ),
        foreground="#555",
        justify=tk.LEFT,
    ).pack(anchor=tk.W, pady=(0, 10))

    table_wrap = ttk.Frame(outer)
    table_wrap.pack(fill=tk.BOTH, expand=True)

    canvas = tk.Canvas(table_wrap, highlightthickness=0)
    scroll = ttk.Scrollbar(table_wrap, orient=tk.VERTICAL, command=canvas.yview)
    inner = ttk.Frame(canvas)
    inner.bind(
        "<Configure>",
        lambda _e: canvas.configure(scrollregion=canvas.bbox("all")),
    )
    canvas.create_window((0, 0), window=inner, anchor=tk.NW)
    canvas.configure(yscrollcommand=scroll.set)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)

    header = ttk.Frame(inner)
    header.pack(fill=tk.X, pady=(0, 4))
    headers = [
        ("성명", 9),
        ("당월\n연차", 6),
        ("잔여\n연차", 7),
        ("유급\n연차", 8),
        (f"휴업\n({pay_rate:g}%)", 8),
        ("무급\n결근", 8),
    ]
    for col, (text, width) in enumerate(headers):
        ttk.Label(header, text=text, width=width, font=("맑은 고딕", 9, "bold")).grid(
            row=0, column=col, sticky=tk.W, padx=2
        )

    case_by_key = {c["name_key"]: c for c in cases}

    def _format_days(value: float) -> str:
        return str(int(value)) if value == int(value) else f"{value:g}"

    def _read_row(state: dict[str, Any]) -> tuple[float, float, float]:
        annual = _parse_days(state["annual_var"].get())
        if state.get("paid_locked"):
            annual = 0.0
        else:
            annual = min(annual, state["max_paid"])
        shutdown = _parse_days(state["shutdown_var"].get())
        unpaid = _parse_days(state["unpaid_var"].get())
        return annual, shutdown, unpaid

    def _write_row(state: dict[str, Any], annual: float, shutdown: float, unpaid: float) -> None:
        state["_syncing"] = True
        try:
            if state.get("paid_locked"):
                annual = 0.0
            else:
                annual = min(max(0.0, annual), state["max_paid"])
            month = state["month_used"]
            total = annual + shutdown + unpaid
            if abs(total - month) > 1e-9:
                unpaid = max(0.0, month - annual - shutdown)
            state["annual_var"].set(_format_days(annual))
            state["shutdown_var"].set(_format_days(shutdown))
            state["unpaid_var"].set(_format_days(unpaid))
        finally:
            state["_syncing"] = False

    def _bind_row(state: dict[str, Any]) -> None:
        def _on_annual(*_a: object) -> None:
            if state.get("_syncing"):
                return
            month = state["month_used"]
            annual = min(_parse_days(state["annual_var"].get()), state["max_paid"])
            if state.get("paid_locked"):
                annual = 0.0
            _, shutdown, unpaid = _read_row(state)
            if annual + shutdown + unpaid > month + 1e-9:
                unpaid = max(0.0, month - annual - shutdown)
            _write_row(state, annual, shutdown, unpaid)

        def _on_shutdown(*_a: object) -> None:
            if state.get("_syncing"):
                return
            month = state["month_used"]
            annual, shutdown, unpaid = _read_row(state)
            max_shutdown = max(0.0, month - annual)
            shutdown = min(shutdown, max_shutdown)
            unpaid = max(0.0, month - annual - shutdown)
            _write_row(state, annual, shutdown, unpaid)

        def _on_unpaid(*_a: object) -> None:
            if state.get("_syncing"):
                return
            month = state["month_used"]
            annual, shutdown, unpaid = _read_row(state)
            unpaid = min(unpaid, month)
            shutdown = max(0.0, month - annual - unpaid)
            _write_row(state, annual, shutdown, unpaid)

        if not state.get("paid_locked"):
            state["annual_var"].trace_add("write", _on_annual)
        state["shutdown_var"].trace_add("write", _on_shutdown)
        state["unpaid_var"].trace_add("write", _on_unpaid)

    for case in cases:
        key = case["name_key"]
        month_used = max(0.0, safe_number(case.get("month_used"), 0.0))
        max_paid = _max_paid_days(case)
        paid_locked = max_paid <= 1e-9
        defaults = default_leave_split_for_case(case)
        month_choices = _day_choices(month_used)

        if paid_locked:
            annual_choices = ["0"]
            defaults = {
                "annual_days": 0.0,
                "shutdown_days": 0.0,
                "unpaid_days": month_used,
            }
        else:
            annual_choices = _day_choices(min(month_used, max_paid))

        annual_var = tk.StringVar(value=_format_days(defaults["annual_days"]))
        shutdown_var = tk.StringVar(value=_format_days(defaults.get("shutdown_days", 0.0)))
        unpaid_var = tk.StringVar(value=_format_days(defaults["unpaid_days"]))

        state = {
            "key": key,
            "month_used": month_used,
            "max_paid": max_paid,
            "paid_locked": paid_locked,
            "annual_var": annual_var,
            "shutdown_var": shutdown_var,
            "unpaid_var": unpaid_var,
        }
        row_state.append(state)

        row_f = ttk.Frame(inner)
        row_f.pack(fill=tk.X, pady=3)

        month_disp = int(month_used) if month_used == int(month_used) else month_used
        ttk.Label(row_f, text=case["name"], width=9).grid(row=0, column=0, sticky=tk.W, padx=2)
        ttk.Label(row_f, text=f"{month_disp}일", width=6).grid(row=0, column=1, padx=2)
        ttk.Label(row_f, text=case["remaining_display"], width=7).grid(row=0, column=2, padx=2)

        annual_cb = ttk.Combobox(
            row_f,
            textvariable=annual_var,
            values=annual_choices,
            width=7,
            state="disabled" if paid_locked else "readonly",
        )
        annual_cb.grid(row=0, column=3, padx=2)
        shutdown_cb = ttk.Combobox(
            row_f,
            textvariable=shutdown_var,
            values=month_choices,
            width=7,
            state="readonly",
        )
        shutdown_cb.grid(row=0, column=4, padx=2)
        unpaid_cb = ttk.Combobox(
            row_f,
            textvariable=unpaid_var,
            values=month_choices,
            width=7,
            state="readonly",
        )
        unpaid_cb.grid(row=0, column=5, padx=2)

        _bind_row(state)

    bulk = ttk.Frame(outer)
    bulk.pack(fill=tk.X, pady=(10, 0))

    def apply_bulk(mode: str) -> None:
        for state in row_state:
            case = case_by_key[state["key"]]
            month = state["month_used"]
            max_p = state["max_paid"]
            if mode == "grant":
                if state.get("paid_locked"):
                    annual, shutdown, unpaid = 0.0, 0.0, month
                else:
                    annual = min(month, max_p)
                    shutdown, unpaid = 0.0, max(0.0, month - annual)
            elif mode == "shutdown":
                if state.get("paid_locked"):
                    annual, shutdown, unpaid = 0.0, month, 0.0
                else:
                    annual = min(month, max_p)
                    shutdown = max(0.0, month - annual)
                    unpaid = 0.0
            elif mode == "unpaid":
                annual, shutdown, unpaid = 0.0, 0.0, month
            else:
                split = default_leave_split_for_case(case)
                annual = split["annual_days"]
                shutdown = split.get("shutdown_days", 0.0)
                unpaid = split["unpaid_days"]
            _write_row(state, annual, shutdown, unpaid)

    ttk.Button(bulk, text="전원: 잔여만큼 유급", command=lambda: apply_bulk("split"), width=15).pack(
        side=tk.LEFT, padx=(0, 4)
    )
    ttk.Button(bulk, text="전원: 휴업(회사)", command=lambda: apply_bulk("shutdown"), width=14).pack(
        side=tk.LEFT, padx=(0, 4)
    )
    ttk.Button(bulk, text="전원: 무급/결근", command=lambda: apply_bulk("unpaid"), width=14).pack(
        side=tk.LEFT, padx=(0, 4)
    )
    ttk.Button(bulk, text="전원: 연차 부여", command=lambda: apply_bulk("grant"), width=12).pack(
        side=tk.LEFT
    )

    btn_row = ttk.Frame(win, padding=(12, 0, 12, 12))
    btn_row.pack(fill=tk.X)

    def on_ok() -> None:
        nonlocal result
        out: dict[str, dict[str, float]] = {}
        for state in row_state:
            key = state["key"]
            month = state["month_used"]
            annual, shutdown, unpaid = _read_row(state)
            if abs(annual + shutdown + unpaid - month) > 0.01:
                messagebox.showerror(
                    "일수 확인",
                    f"{case_by_key[key]['name']}: 유급({annual}일)+휴업({shutdown}일)+"
                    f"무급({unpaid}일)={annual + shutdown + unpaid}일\n"
                    f"당월 연차 {month}일과 맞춰 주세요.",
                    parent=win,
                )
                return
            max_paid = _max_paid_days(case_by_key[key])
            if annual > max_paid + 1e-9:
                if max_paid <= 1e-9:
                    messagebox.showerror(
                        "유급 연차 불가",
                        f"{case_by_key[key]['name']}: 잔여 연차가 없어 유급 연차를 부여할 수 없습니다.",
                        parent=win,
                    )
                else:
                    messagebox.showerror(
                        "유급 연차 초과",
                        f"{case_by_key[key]['name']}: 유급 연차는 잔여 {max_paid:g}일까지입니다.",
                        parent=win,
                    )
                return
            out[key] = {
                "annual_days": annual,
                "shutdown_days": shutdown,
                "unpaid_days": unpaid,
            }
        result = out
        win.destroy()

    def on_cancel() -> None:
        nonlocal result
        result = None
        win.destroy()

    ttk.Button(btn_row, text="확인 후 급여 산출", command=on_ok, width=16).pack(side=tk.RIGHT, padx=(8, 0))
    ttk.Button(btn_row, text="취소", command=on_cancel, width=12).pack(side=tk.RIGHT)

    win.protocol("WM_DELETE_WINDOW", on_cancel)
    win.update_idletasks()
    px = parent.winfo_rootx() + max((parent.winfo_width() - win.winfo_width()) // 2, 0)
    py = parent.winfo_rooty() + max((parent.winfo_height() - win.winfo_height()) // 2, 0)
    win.geometry(f"+{px}+{py}")
    win.wait_window()
    return result
