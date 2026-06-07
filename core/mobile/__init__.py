"""현장 근로자 모바일 앱 연동 — 출퇴근·지오펜스·생체인증·급여 연동."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["app_api", "models", "payroll_source", "profile", "store", "sync", "workflow_bridge"]


def __getattr__(name: str) -> Any:
    if name in __all__:
        module = import_module(f"core.mobile.{name}")
        globals()[name] = module
        return module
    raise AttributeError(name)
