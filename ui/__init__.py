"""UI 컴포넌트.

Keep package imports lightweight so importing a specific UI surface does not
eagerly load optional preview/export dependencies.
"""

from __future__ import annotations

from typing import Any

__all__ = ["FilePreviewPanel"]


def __getattr__(name: str) -> Any:
    if name == "FilePreviewPanel":
        from ui.preview_panel import FilePreviewPanel

        return FilePreviewPanel
    raise AttributeError(name)
