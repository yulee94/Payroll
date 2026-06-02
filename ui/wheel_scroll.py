"""
ui/wheel_scroll.py - 앱 전역 마우스 휠 스크롤 (Windows / macOS / Linux)
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


def wheel_delta(event) -> int:
    """휠 방향: 위로 스크롤 시 음수(내용 위로)."""
    if getattr(event, "num", None) == 5:
        return 1
    if getattr(event, "num", None) == 4:
        return -1
    if event.delta:
        return int(-1 * (event.delta / 120))
    return 0


def _scroll_widget(widget: tk.Misc, delta: int, event) -> bool:
    if delta == 0:
        return False
    try:
        if isinstance(widget, ttk.Treeview):
            widget.yview_scroll(delta, "units")
            return True
        if isinstance(widget, tk.Text):
            widget.yview_scroll(delta, "units")
            return True
        if isinstance(widget, tk.Canvas):
            if event.state & 0x0001:
                widget.xview_scroll(delta, "units")
            else:
                widget.yview_scroll(delta, "units")
            return True
        if isinstance(widget, tk.Listbox):
            widget.yview_scroll(delta, "units")
            return True
    except tk.TclError:
        return False
    return False


def find_scroll_target(widget: tk.Misc | None) -> tk.Misc | None:
    """이벤트 위치에서 스크롤 가능한 위젯을 찾습니다."""
    w: tk.Misc | None = widget
    while w is not None:
        if isinstance(w, (ttk.Treeview, tk.Text, tk.Canvas, tk.Listbox)):
            try:
                if isinstance(w, tk.Canvas):
                    return w
                if isinstance(w, (ttk.Treeview, tk.Text, tk.Listbox)):
                    return w
            except tk.TclError:
                pass
        w = getattr(w, "master", None)
    return None


def on_global_mousewheel(event) -> str | None:
    delta = wheel_delta(event)
    if delta == 0:
        return None
    target = find_scroll_target(event.widget)
    if target and _scroll_widget(target, delta, event):
        return "break"
    return None


def install_global_wheel(root: tk.Misc) -> None:
    """대시보드 루트에 전역 휠 바인딩 (한 번만)."""
    if getattr(root, "_wheel_scroll_installed", False):
        return
    root._wheel_scroll_installed = True  # type: ignore[attr-defined]

    root.bind_all("<MouseWheel>", on_global_mousewheel, add="+")
    root.bind_all("<Shift-MouseWheel>", on_global_mousewheel, add="+")
    root.bind_all("<Button-4>", on_global_mousewheel, add="+")
    root.bind_all("<Button-5>", on_global_mousewheel, add="+")


def bind_local_wheel(widget: tk.Misc, scroll_target: tk.Misc | None = None) -> None:
    """특정 위젯 트리에 로컬 휠 바인딩 (선택)."""
    target = scroll_target or widget

    def _handler(event, t=target) -> str:
        delta = wheel_delta(event)
        if delta and _scroll_widget(t, delta, event):
            return "break"
        return on_global_mousewheel(event) or "break"

    widget.bind("<MouseWheel>", _handler, add="+")
    widget.bind("<Button-4>", _handler, add="+")
    widget.bind("<Button-5>", _handler, add="+")
