"""
ui/spreadsheet_grid.py - Excel 유사 스프레드시트 미리보기 그리드 (열 필터)
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from services.preview_export import GridRow, PreviewData
from services.preview_grid_filter import (
    apply_grid_filters,
    column_distinct_values,
    column_header_label,
    count_data_rows,
    filterable_columns,
    find_header_row_index,
    format_filter_summary,
)
from ui.spreadsheet_filter_popup import ColumnFilterPopup
from ui.theme import COLORS, FONT


class SpreadsheetGrid(ttk.Frame):
    """제목·헤더·데이터 행 스타일이 적용된 표 형태 미리보기."""

    _ROLE_STYLES: dict[str, dict[str, str]] = {
        "corner": {"bg": "#E2E8F0", "fg": "#475569", "font": (FONT, 8, "bold")},
        "col_head": {"bg": "#CBD5E1", "fg": "#334155", "font": (FONT, 8, "bold")},
        "row_num": {"bg": "#F1F5F9", "fg": "#64748B", "font": (FONT, 8)},
        "title": {"bg": COLORS["table_head"], "fg": "#FFFFFF", "font": (FONT, 11, "bold")},
        "subtitle": {"bg": "#E0E7FF", "fg": COLORS["accent"], "font": (FONT, 10)},
        "section": {"bg": "#F1F5F9", "fg": COLORS["text"], "font": (FONT, 10, "bold")},
        "header": {"bg": COLORS["table_head"], "fg": "#FFFFFF", "font": (FONT, 9, "bold")},
        "header_filter": {"bg": "#1E40AF", "fg": "#FFFFFF", "font": (FONT, 9, "bold")},
        "data": {"bg": "#FFFFFF", "fg": COLORS["text"], "font": (FONT, 9)},
        "data_alt": {"bg": "#F8FAFC", "fg": COLORS["text"], "font": (FONT, 9)},
        "empty": {"bg": "#FFFFFF", "fg": COLORS["text"], "font": (FONT, 9)},
    }

    _ROW_NUM_WIDTH = 44

    def __init__(
        self,
        parent,
        colors: dict[str, str] | None = None,
        *,
        on_filter_changed: Callable[[str], None] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(parent, **kwargs)
        self._colors = colors or COLORS
        self._col_minsizes: list[int] = []
        self._on_filter_changed = on_filter_changed
        self._source: PreviewData | None = None
        self._column_filters: dict[int, frozenset[str]] = {}
        self._filterable_cols: set[int] = set()
        self._header_row_idx: int | None = None
        self._filter_popup: ColumnFilterPopup | None = None

        self.canvas = tk.Canvas(self, bg="#FFFFFF", highlightthickness=1, highlightbackground=COLORS["border"])
        self.v_scroll = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.h_scroll = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.v_scroll.grid(row=0, column=1, sticky="ns")
        self.h_scroll.grid(row=1, column=0, sticky="ew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._inner = tk.Frame(self.canvas, bg="#FFFFFF")
        self._window_id = self.canvas.create_window((0, 0), window=self._inner, anchor=tk.NW)
        self._inner.bind("<Configure>", self._on_inner_configure)
        from ui.wheel_scroll import bind_local_wheel

        for w in (self, self.canvas, self._inner):
            bind_local_wheel(w, self.canvas)

    def _bind_wheel_descendants(self, widget: tk.Misc) -> None:
        from ui.wheel_scroll import bind_local_wheel

        for child in widget.winfo_children():
            bind_local_wheel(child, self.canvas)
            self._bind_wheel_descendants(child)

    def _on_inner_configure(self, _event=None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def clear(self) -> None:
        for child in self._inner.winfo_children():
            child.destroy()
        self._col_minsizes = []
        self._source = None
        self._column_filters = {}
        self._filterable_cols = set()
        self._header_row_idx = None

    def clear_filters(self) -> None:
        if not self._column_filters:
            return
        self._column_filters = {}
        if self._source:
            self._render()
        self._notify_filter_change()

    @property
    def has_active_filters(self) -> bool:
        return bool(self._column_filters)

    def has_filterable_columns(self, data: PreviewData | None = None) -> bool:
        src = data or self._source
        if not src or not src.grid_rows:
            return False
        return bool(filterable_columns(src.grid_rows, src.column_count))

    def filter_summary(self) -> str:
        if not self._source or not self._source.grid_rows:
            return ""
        visible = self._filtered_rows()
        return format_filter_summary(
            self._source.grid_rows,
            self._column_filters,
            visible_rows=visible,
        )

    def load(self, data: PreviewData) -> None:
        self._source = data
        self._column_filters = {}
        self._render()

    def _filtered_rows(self) -> list[GridRow]:
        if not self._source:
            return []
        return apply_grid_filters(self._source.grid_rows, self._column_filters)

    def _notify_filter_change(self) -> None:
        if self._on_filter_changed:
            self._on_filter_changed(self.filter_summary())

    def _render(self) -> None:
        for child in self._inner.winfo_children():
            child.destroy()
        self._col_minsizes = []

        data = self._source
        if not data or not data.grid_rows or data.column_count <= 0:
            tk.Label(
                self._inner,
                text="표시할 데이터가 없습니다.",
                bg="#FFFFFF",
                fg=self._colors["muted"],
                font=(FONT, 10),
                padx=16,
                pady=16,
            ).pack()
            self._on_inner_configure()
            return

        grid_rows = self._filtered_rows()
        ncol = data.column_count
        self._header_row_idx = find_header_row_index(data.grid_rows)
        self._filterable_cols = set(filterable_columns(data.grid_rows, ncol))

        col_widths = self._calc_col_widths(data.grid_rows, ncol)
        self._col_minsizes = col_widths

        self._inner.grid_columnconfigure(0, minsize=self._ROW_NUM_WIDTH, weight=0)
        for c, w in enumerate(col_widths, start=1):
            self._inner.grid_columnconfigure(c, minsize=w, weight=0)

        self._cell(0, 0, "", "corner", min_width=self._ROW_NUM_WIDTH, sticky="nsew")
        for c in range(ncol):
            letter = data.column_letters[c] if c < len(data.column_letters) else str(c + 1)
            self._cell(0, c + 1, letter, "col_head", min_width=col_widths[c], sticky="nsew")

        data_row_idx = 0
        for r, grow in enumerate(grid_rows, start=1):
            if grow.role == "empty":
                self._cell(r, 0, str(grow.index), "row_num", min_width=self._ROW_NUM_WIDTH, pady=2, sticky="nsew")
                for c in range(ncol):
                    self._cell(r, c + 1, "", "empty", min_width=col_widths[c], pady=2, sticky="nsew")
                continue

            self._cell(r, 0, str(grow.index), "row_num", min_width=self._ROW_NUM_WIDTH, sticky="nsew")

            if grow.role in ("title", "subtitle", "section"):
                text = self._merged_text(grow.cells)
                self._cell(r, 1, text, grow.role, colspan=ncol, sticky="ew")
                continue

            style = grow.role
            if grow.role == "header":
                for c in range(ncol):
                    val = grow.cells[c] if c < len(grow.cells) else ""
                    if c in self._filterable_cols:
                        self._filter_header_cell(
                            r,
                            c + 1,
                            val,
                            data_col=c,
                            min_width=col_widths[c],
                            active=c in self._column_filters,
                        )
                    else:
                        self._cell(r, c + 1, val, "header", min_width=col_widths[c], anchor="center", sticky="nsew")
                continue

            if grow.role == "data":
                data_row_idx += 1
                style = "data_alt" if data_row_idx % 2 == 0 else "data"

            for c in range(ncol):
                val = grow.cells[c] if c < len(grow.cells) else ""
                align = grow.aligns[c] if c < len(grow.aligns) else "w"
                self._cell(r, c + 1, val, style, min_width=col_widths[c], anchor=align, sticky="nsew")

        self._inner.update_idletasks()
        total_w = self._ROW_NUM_WIDTH + sum(col_widths)
        self.canvas.itemconfig(self._window_id, width=total_w)
        self._on_inner_configure()
        self.canvas.xview_moveto(0)
        self._bind_wheel_descendants(self._inner)

    def _open_column_filter(self, col: int) -> None:
        if not self._source or self._filter_popup is not None:
            return
        if col not in self._filterable_cols:
            return
        values = column_distinct_values(self._source.grid_rows, col)
        if not values:
            return
        label = column_header_label(self._source.grid_rows, self._header_row_idx, col)
        current = self._column_filters.get(col)
        selected = set(current) if current else set(values)

        def on_apply(chosen: set[str] | None) -> None:
            self._filter_popup = None
            if chosen is None:
                self._column_filters.pop(col, None)
            else:
                self._column_filters[col] = frozenset(chosen)
            self._render()
            self._notify_filter_change()

        self._filter_popup = ColumnFilterPopup(
            self.winfo_toplevel(),
            column_label=label,
            values=values,
            selected=selected,
            on_apply=on_apply,
        )
        self._filter_popup.bind("<Destroy>", lambda _e: setattr(self, "_filter_popup", None))

    def _filter_header_cell(
        self,
        row: int,
        col: int,
        text: str,
        *,
        data_col: int,
        min_width: int,
        active: bool,
    ) -> tk.Frame:
        style_key = "header_filter" if active else "header"
        style = self._ROLE_STYLES[style_key]
        frame = tk.Frame(
            self._inner,
            bg=style["bg"],
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["border"],
            cursor="hand2",
        )
        frame.grid(row=row, column=col, sticky="nsew")

        display = str(text or "").replace("\n", " ")
        lbl = tk.Label(
            frame,
            text=display,
            bg=style["bg"],
            fg=style["fg"],
            font=style["font"],
            padx=6,
            pady=6,
            anchor=tk.CENTER,
            cursor="hand2",
        )
        lbl.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        icon = tk.Label(
            frame,
            text="▼",
            bg=style["bg"],
            fg="#FDE68A" if active else "#E2E8F0",
            font=(FONT, 8, "bold"),
            padx=4,
            cursor="hand2",
        )
        icon.pack(side=tk.RIGHT)

        for w in (frame, lbl, icon):
            w.bind("<Button-1>", lambda _e, dc=data_col: self._open_column_filter(dc))
        return frame

    def _merged_text(self, cells: list[str]) -> str:
        return "  ".join(c.strip() for c in cells if c.strip())

    def _calc_col_widths(self, rows: list[GridRow], ncol: int) -> list[int]:
        widths = [80] * ncol
        for grow in rows:
            if grow.role in ("title", "subtitle", "section", "empty"):
                continue
            for c in range(min(ncol, len(grow.cells))):
                val = grow.cells[c]
                line = val.split("\n")[0]
                char_w = min(max(len(line), 5), 48)
                widths[c] = max(widths[c], char_w * 9 + 20)
        return [min(w, 360) for w in widths]

    def _cell(
        self,
        row: int,
        col: int,
        text: str,
        style_key: str,
        min_width: int = 88,
        pady: int = 6,
        anchor: str = "w",
        colspan: int = 1,
        sticky: str = "nsew",
    ) -> tk.Label:
        style = self._ROLE_STYLES.get(style_key, self._ROLE_STYLES["data"])

        anchor_map = {"w": tk.W, "e": tk.E, "center": tk.CENTER}
        tk_anchor = anchor_map.get(anchor, tk.W)

        display = text.replace("\n", " ↵ ")
        lbl = tk.Label(
            self._inner,
            text=display,
            bg=style["bg"],
            fg=style["fg"],
            font=style["font"],
            padx=8,
            pady=pady,
            anchor=tk_anchor,
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["border"],
        )
        lbl.grid(row=row, column=col, columnspan=colspan, sticky=sticky)
        return lbl
