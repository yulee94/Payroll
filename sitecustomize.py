"""
sitecustomize.py - Bitween desktop runtime integrations.

Python imports this file automatically on startup when the project directory is
on sys.path. It keeps main.py and the large Tkinter dashboard stable while
installing small runtime integrations as app_ui is imported.
"""

from __future__ import annotations

import builtins
import sys
from types import ModuleType
from typing import Any

_PATCHING = False


def _patch_app_ui_module(module: ModuleType | None = None) -> None:
    global _PATCHING
    if _PATCHING:
        return
    target = module or sys.modules.get("app_ui")
    if target is None or getattr(target, "_bitween_payroll_integrations_installed", False):
        return
    if getattr(target, "PayrollDashboard", None) is None:
        return

    _PATCHING = True
    try:
        from services.payroll_ui_bridge import install_app_ui_integrations

        install_app_ui_integrations(target)
    except Exception:
        # sitecustomize must never block normal interpreter startup.
        pass
    finally:
        _PATCHING = False


if not getattr(builtins, "_bitween_import_hook_installed", False):
    _ORIGINAL_IMPORT = builtins.__import__

    def _bitween_import(
        name: str,
        globals: dict[str, Any] | None = None,
        locals: dict[str, Any] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> Any:
        module = _ORIGINAL_IMPORT(name, globals, locals, fromlist, level)
        if name == "app_ui" or name.endswith(".app_ui") or "app_ui" in sys.modules:
            _patch_app_ui_module(sys.modules.get("app_ui"))
        return module

    builtins.__import__ = _bitween_import
    builtins._bitween_import_hook_installed = True
else:
    _patch_app_ui_module(sys.modules.get("app_ui"))
