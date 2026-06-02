"""
ui/org_filter_bar.py - 계열사·사업장 필터 (월은 헤더 급여월과 연동)
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from services.org_registry import ALL_LABEL, OrgSelection, list_affiliate_options, list_workplace_options
from ui.theme import COLORS, FONT


class OrgFilterBar(ttk.Frame):
    """계열사 → 사업장 연동 필터."""

    def __init__(
        self,
        parent,
        on_change: Callable[[OrgSelection], None] | None = None,
        show_hint: bool = True,
        **kwargs,
    ) -> None:
        super().__init__(parent, **kwargs)
        self._on_change = on_change
        self._records: list = []
        self._updating = False

        ttk.Label(self, text="계열사", font=(FONT, 9, "bold")).pack(side=tk.LEFT, padx=(0, 6))
        self._aff_var = tk.StringVar(value=ALL_LABEL)
        self._aff_combo = ttk.Combobox(
            self,
            textvariable=self._aff_var,
            state="readonly",
            width=18,
            font=(FONT, 9),
        )
        self._aff_combo.pack(side=tk.LEFT, padx=(0, 14))
        self._aff_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_affiliate_changed())

        ttk.Label(self, text="사업장", font=(FONT, 9, "bold")).pack(side=tk.LEFT, padx=(0, 6))
        self._wp_var = tk.StringVar(value=ALL_LABEL)
        self._wp_combo = ttk.Combobox(
            self,
            textvariable=self._wp_var,
            state="readonly",
            width=20,
            font=(FONT, 9),
        )
        self._wp_combo.pack(side=tk.LEFT, padx=(0, 14))
        self._wp_combo.bind("<<ComboboxSelected>>", lambda _e: self._emit())

        if show_hint:
            tk.Label(
                self,
                text="급여월은 상단에서 선택",
                bg=COLORS["bg"],
                fg=COLORS["muted"],
                font=(FONT, 8),
            ).pack(side=tk.LEFT, padx=(8, 0))

        self._set_affiliate_values([ALL_LABEL])

    def set_records(self, records: list | None) -> None:
        self._records = records or []
        affs = list_affiliate_options(self._records)
        current = self._aff_var.get()
        self._set_affiliate_values(affs)
        if current in affs:
            self._aff_var.set(current)
        else:
            self._aff_var.set(ALL_LABEL)
        self._refresh_workplaces()

    def reset(self) -> None:
        self._records = []
        self._aff_var.set(ALL_LABEL)
        self._set_affiliate_values([ALL_LABEL])
        self._refresh_workplaces()

    def get_selection(self) -> OrgSelection:
        return OrgSelection(
            affiliate=self._aff_var.get() or ALL_LABEL,
            workplace=self._wp_var.get() or ALL_LABEL,
        )

    def _set_affiliate_values(self, values: list[str]) -> None:
        self._aff_combo.configure(values=values)

    def _on_affiliate_changed(self) -> None:
        self._refresh_workplaces()
        self._emit()

    def _refresh_workplaces(self) -> None:
        self._updating = True
        wps = list_workplace_options(self._records, self._aff_var.get())
        current = self._wp_var.get()
        self._wp_combo.configure(values=wps)
        if current in wps:
            self._wp_var.set(current)
        else:
            self._wp_var.set(ALL_LABEL)
        self._updating = False

    def _emit(self) -> None:
        if self._updating or not self._on_change:
            return
        self._on_change(self.get_selection())
