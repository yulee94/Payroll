"""

ui/kpi_map_view.py - 지역 단위 경영 지도 (대한민국 지도 + 손익 버블)

"""



from __future__ import annotations



import tkinter as tk

from typing import Any, Callable



from core.kpi.service import STATUS_CRITICAL, STATUS_OK, STATUS_WARN

from ui.kpi_map_assets import load_korea_map_photo, map_content_rect, pin_xy

from ui.theme import COLORS, FONT





def _won_label(n: int) -> str:

    if abs(n) >= 100_000_000:

        return f"{n / 100_000_000:.1f}억"

    if abs(n) >= 10_000:

        return f"{n / 10_000:,.0f}만"

    return f"{n:,}"





class KpiMapView(tk.Frame):

    """대한민국 지도 위 지역별 집계 — 클릭 시 하단 패널에서 사업장 목록 드릴다운."""



    BUBBLE_R = 28



    def __init__(

        self,

        parent: tk.Misc,

        *,

        on_select: Callable[[dict[str, Any] | None], None] | None = None,

        **kwargs: Any,

    ) -> None:

        super().__init__(parent, bg=COLORS["card"], **kwargs)

        self._on_select = on_select

        self._regions: list[dict[str, Any]] = []

        self._bubbles: dict[str, int] = {}

        self._bubble_region: dict[int, dict[str, Any]] = {}

        self._selected_id: str | None = None

        self._map_photo: tk.PhotoImage | None = None

        self._map_img_size = (0, 0)

        self._map_rect = (0, 0, 0, 0)

        self._tooltip: tk.Toplevel | None = None

        self._tooltip_lbl: tk.Label | None = None

        self._hover_bubble_item: int | None = None
        self._redraw_job: str | None = None
        self._redraw_debounce_ms = 120
        self._map_cache_size: tuple[int, int] = (0, 0)

        self.grid_rowconfigure(0, weight=1)

        self.grid_columnconfigure(0, weight=1)



        wrap = tk.Frame(self, bg="#E8F0FE", highlightbackground="#BFDBFE", highlightthickness=1)

        wrap.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

        wrap.grid_rowconfigure(0, weight=1)

        wrap.grid_columnconfigure(0, weight=1)



        self._canvas = tk.Canvas(wrap, bg="#EEF4FF", highlightthickness=0, height=260)

        self._canvas.grid(row=0, column=0, sticky="nsew")

        self._canvas.bind("<Configure>", lambda _e: self._schedule_redraw())

        self._canvas.bind("<Button-1>", self._on_click)

        self._canvas.bind("<Motion>", self._on_motion)

        self._canvas.bind("<Leave>", lambda _e: self._hide_tooltip())



        legend = tk.Frame(wrap, bg="#E8F0FE")

        legend.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))

        tk.Label(

            legend,

            text="대한민국 지도 · 지역 클릭 → 아래 사업장 목록",

            bg="#E8F0FE",

            fg="#64748B",

            font=(FONT, 8),

        ).pack(side=tk.LEFT, padx=(0, 16))

        for text, color in (

            ("● 흑자", "#2563EB"),

            ("● 주의", "#D97706"),

            ("● 적자·위험", "#DC2626"),

            ("▣ 음영 = 이슈 지역", "#64748B"),

        ):

            tk.Label(legend, text=text, bg="#E8F0FE", fg=color, font=(FONT, 8)).pack(side=tk.LEFT, padx=(0, 12))



    def load_regions(self, regions: list[dict[str, Any]]) -> None:

        self._regions = list(regions)

        self._redraw()



    def select_region(self, region_id: str | None) -> None:

        self._selected_id = region_id

        self._redraw()



    def _region_color(self, region: dict[str, Any]) -> str:

        status = str(region.get("status") or "")

        profit = int(region.get("profit") or 0)

        if status == STATUS_CRITICAL or profit < 0:

            return "#DC2626"

        if status == STATUS_WARN:

            return "#D97706"

        return "#2563EB"



    def _schedule_redraw(self) -> None:
        if self._redraw_job is not None:
            try:
                self.after_cancel(self._redraw_job)
            except Exception:
                pass
        self._redraw_job = self.after(self._redraw_debounce_ms, self._run_scheduled_redraw)

    def _run_scheduled_redraw(self) -> None:
        self._redraw_job = None
        self._redraw()

    def _load_map_background(self, w: int, h: int) -> None:
        title_h = 28
        size_key = (max(w - 16, 1), max(h - title_h - 12, 1))
        if self._map_photo is not None and self._map_cache_size == size_key:
            return

        photo, iw, ih = load_korea_map_photo(self._canvas, max_width=size_key[0], max_height=size_key[1])

        self._map_photo = photo
        self._map_cache_size = size_key
        self._map_img_size = (iw, ih)

        if photo and iw and ih:

            self._map_rect = map_content_rect(w, h, iw, ih, title_h=title_h)

        else:

            self._map_rect = (8, title_h, w - 16, h - title_h - 8)



    def _redraw(self) -> None:

        c = self._canvas

        c.delete("all")

        self._bubbles.clear()

        self._bubble_region.clear()

        w = max(c.winfo_width(), 520)

        h = max(c.winfo_height(), 280)



        c.create_rectangle(0, 0, w, h, fill="#EEF4FF", outline="")

        c.create_text(

            w * 0.5,

            14,

            text="COSS Group · 지역별 손익 현황",

            fill="#475569",

            font=(FONT, 9, "bold"),

        )



        self._load_map_background(w, h)

        x0, y0, nw, nh = self._map_rect

        if self._map_photo is not None:

            c.create_image(x0, y0, anchor=tk.NW, image=self._map_photo, tags=("map_bg",))



        if not self._regions:

            c.create_text(w * 0.5, h * 0.55, text="표시할 지역 데이터가 없습니다.", fill="#94A3B8", font=(FONT, 10))

            return



        for region in self._regions:

            rid = str(region.get("id") or "")

            mx = float(region.get("map_x") or 0.5)

            my = float(region.get("map_y") or 0.5)

            x, y = pin_xy(mx, my, x0, y0, nw, nh)

            color = self._region_color(region)

            profit = int(region.get("profit") or 0)

            margin = float(region.get("margin_pct") or 0)

            label = str(region.get("label") or region.get("region") or "")

            count = int(region.get("site_count") or 0)

            issues = int(region.get("issue_count") or 0)

            status = str(region.get("status") or STATUS_OK)



            if issues > 0:

                c.create_oval(

                    x - self.BUBBLE_R - 8,

                    y - self.BUBBLE_R - 8,

                    x + self.BUBBLE_R + 8,

                    y + self.BUBBLE_R + 8,

                    fill="#DC2626",

                    outline="",

                    stipple="gray25",

                )



            outline = "#0F172A" if rid == self._selected_id else color

            width = 3 if rid == self._selected_id else 2

            oid = c.create_oval(

                x - self.BUBBLE_R,

                y - self.BUBBLE_R,

                x + self.BUBBLE_R,

                y + self.BUBBLE_R,

                fill=color,

                outline=outline,

                width=width,

            )

            self._bubbles[rid] = oid

            self._bubble_region[oid] = region



            sign = "+" if profit >= 0 else ""

            c.create_text(x, y - 10, text=label[:7], fill="#FFFFFF", font=(FONT, 7, "bold"))

            c.create_text(x, y + 2, text=f"{count}곳", fill="#E0F2FE", font=(FONT, 7))

            c.create_text(x, y + 13, text=f"{sign}{_won_label(profit)}", fill="#FFFFFF", font=(FONT, 8, "bold"))

            c.create_text(

                x,

                y + 26,

                text=f"{margin:+.1f}%",

                fill="#E0F2FE" if profit >= 0 else "#FEE2E2",

                font=(FONT, 7),

            )

            if issues > 0:

                c.create_text(

                    x + self.BUBBLE_R - 6,

                    y - self.BUBBLE_R + 6,

                    text=str(issues),

                    fill="#FFFFFF",

                    font=(FONT, 8, "bold"),

                )



    def _on_click(self, event: tk.Event) -> None:

        c = self._canvas

        items = c.find_overlapping(event.x - 2, event.y - 2, event.x + 2, event.y + 2)

        picked: dict[str, Any] | None = None

        for region in self._regions:

            rid = str(region.get("id") or "")

            if self._bubbles.get(rid) in items:

                picked = region

                self._selected_id = rid

                break

        if picked is None:

            self._selected_id = None

        self._redraw()

        if self._on_select:

            self._on_select(picked)

    def _ensure_tooltip(self) -> None:
        if self._tooltip is not None and self._tooltip.winfo_exists():
            return
        tip = tk.Toplevel(self)
        tip.withdraw()
        tip.overrideredirect(True)
        tip.attributes("-topmost", True)
        tip.configure(bg=COLORS["border"])
        body = tk.Frame(tip, bg=COLORS["card"], padx=10, pady=8)
        body.pack()
        lbl = tk.Label(
            body,
            text="",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=(FONT, 9),
            justify=tk.LEFT,
            anchor=tk.W,
        )
        lbl.pack()
        self._tooltip = tip
        self._tooltip_lbl = lbl

    def _tooltip_text(self, region: dict[str, Any]) -> str:
        label = str(region.get("label") or region.get("region") or "")
        count = int(region.get("site_count") or 0)
        profit = int(region.get("profit") or 0)
        margin = float(region.get("margin_pct") or 0)
        issues = int(region.get("issue_count") or 0)
        status = str(region.get("status") or "")
        sign = "+" if profit >= 0 else ""
        return "\n".join(
            [
                f"【{label}】",
                f"상태: {status} · 이슈: {issues}곳",
                f"사업장: {count}곳",
                f"손익: {sign}{_won_label(profit)} · 마진 {margin:+.1f}%",
            ]
        )

    def _show_tooltip(self, *, x_root: int, y_root: int, region: dict[str, Any]) -> None:
        self._ensure_tooltip()
        if not self._tooltip or not self._tooltip_lbl:
            return
        self._tooltip_lbl.configure(text=self._tooltip_text(region))
        self._tooltip.geometry(f"+{x_root + 16}+{y_root + 12}")
        self._tooltip.deiconify()

    def _hide_tooltip(self) -> None:
        self._hover_bubble_item = None
        if self._tooltip is None:
            return
        if self._tooltip.winfo_exists():
            self._tooltip.withdraw()

    def _on_motion(self, event: tk.Event) -> None:
        c = self._canvas
        items = c.find_overlapping(event.x - 1, event.y - 1, event.x + 1, event.y + 1)
        bubble_item = next((i for i in items if i in self._bubble_region), None)
        if bubble_item is None:
            if self._hover_bubble_item is not None:
                self._hide_tooltip()
            return
        region = self._bubble_region.get(bubble_item)
        if not region:
            return
        self._hover_bubble_item = bubble_item
        self._show_tooltip(x_root=event.x_root, y_root=event.y_root, region=region)


