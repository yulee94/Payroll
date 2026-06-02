"""
dnd_support.py - Windows 파일 드래그앤드롭 (청구서 xlsx)
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

InvoiceDropCallback = Callable[[Path], None]
DropErrorCallback = Callable[[str], None]


def decode_dropped_path(raw: bytes | str) -> Path:
    if isinstance(raw, str):
        return Path(raw.strip().strip('"'))
    for enc in ("utf-8", "cp949", "mbcs"):
        try:
            return Path(raw.decode(enc).strip().strip('"'))
        except UnicodeDecodeError:
            continue
    return Path(raw.decode("utf-8", errors="replace").strip().strip('"'))


def pick_invoice_xlsx(file_list: list) -> Path | None:
    """드롭된 파일 중 첫 번째 .xlsx 반환."""
    for raw in file_list:
        path = decode_dropped_path(raw)
        if path.suffix.lower() == ".xlsx" and path.is_file():
            return path
    return None


def enable_invoice_drop(
    widget,
    on_file: InvoiceDropCallback,
    on_error: DropErrorCallback | None = None,
) -> bool:
    """
    Tk 위젯에 xlsx 드롭을 연결합니다 (Windows).

    Returns:
        True if drag-drop is active, False if windnd unavailable.
    """
    try:
        import windnd
    except ImportError:
        return False

    def _handle_drop(files: list) -> None:
        picked = pick_invoice_xlsx(files)
        if picked is not None:
            widget.after(0, lambda p=picked: on_file(p))
            return
        msg = "도급비 청구서(.xlsx) 파일만 드롭할 수 있습니다."
        if on_error is not None:
            widget.after(0, lambda m=msg: on_error(m))

    windnd.hook_dropfiles(widget, func=_handle_drop)
    return True
