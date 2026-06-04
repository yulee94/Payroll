"""
sitecustomize.py - Bitween desktop runtime integrations.

Python imports this file automatically on startup when the project directory is
on sys.path. It waits for app_ui to finish importing, installs the desktop
runtime integrations once, and then restores Python's normal import behavior.
"""

from __future__ import annotations

import builtins
import sys
from types import ModuleType
from typing import Any

_PATCHING = False


def _uninstall_import_hook() -> None:
    original = getattr(builtins, "_bitween_original_import", None)
    hook = getattr(builtins, "_bitween_import_hook_func", None)
    if original is not None and hook is not None and builtins.__import__ is hook:
        builtins.__import__ = original
    builtins._bitween_import_hook_installed = False


def _patch_app_ui_module(module: ModuleType | None = None) -> bool:
    global _PATCHING
    if _PATCHING:
        return False
    target = module or sys.modules.get("app_ui")
    if target is None or getattr(target, "_bitween_payroll_integrations_installed", False):
        return bool(target is not None)
    if getattr(target, "PayrollDashboard", None) is None:
        return False

    _PATCHING = True
    try:
        from services.payroll_ui_bridge import install_app_ui_integrations

        install_app_ui_integrations(target)
        return bool(getattr(target, "_bitween_payroll_integrations_installed", False))
    except Exception:
        # sitecustomize must never block normal interpreter startup.
        return False
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
            if _patch_app_ui_module(sys.modules.get("app_ui")):
                _uninstall_import_hook()
        return module

    builtins._bitween_original_import = _ORIGINAL_IMPORT
    builtins._bitween_import_hook_func = _bitween_import
    builtins.__import__ = _bitween_import
    builtins._bitween_import_hook_installed = True
else:
    if _patch_app_ui_module(sys.modules.get("app_ui")):
        _uninstall_import_hook()
