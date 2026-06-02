"""
core/module_store.py - 사업부 모듈 공통 JSON 저장소 (테넌트별)
"""

from __future__ import annotations

import json
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

from core.paths import app_data_dir

_lock = threading.Lock()
# (module, tenant_id) -> (mtime_ns, cached dict snapshot)
_db_cache: dict[tuple[str, str], tuple[int, dict[str, Any]]] = {}


def invalidate_module_db_cache(
    module: str | None = None, tenant_id: str | None = None
) -> None:
    """저장·외부 변경 후 캐시 무효화. module/tenant_id 생략 시 전체."""
    with _lock:
        if module is None and tenant_id is None:
            _db_cache.clear()
            return
        drop = [
            k
            for k in _db_cache
            if (module is None or k[0] == module)
            and (tenant_id is None or k[1] == tenant_id)
        ]
        for k in drop:
            del _db_cache[k]


def module_db_path(module: str, tenant_id: str) -> Path:
    return app_data_dir() / module / tenant_id / "database.json"


def load_module_db(module: str, tenant_id: str, empty: dict[str, Any]) -> dict[str, Any]:
    path = module_db_path(module, tenant_id)
    key = (module, tenant_id)
    mtime_ns = path.stat().st_mtime_ns if path.is_file() else 0
    with _lock:
        cached = _db_cache.get(key)
        if cached is not None and cached[0] == mtime_ns:
            return deepcopy(cached[1])
    if not path.is_file():
        out = deepcopy(empty)
        with _lock:
            _db_cache[key] = (0, deepcopy(out))
        return deepcopy(out)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            out = deepcopy(empty)
            for k, default in empty.items():
                if k in data:
                    out[k] = data[k]
            with _lock:
                _db_cache[key] = (mtime_ns, deepcopy(out))
            return deepcopy(out)
    except (OSError, json.JSONDecodeError):
        pass
    out = deepcopy(empty)
    with _lock:
        _db_cache[key] = (mtime_ns, deepcopy(out))
    return deepcopy(out)


def save_module_db(module: str, tenant_id: str, data: dict[str, Any]) -> None:
    path = module_db_path(module, tenant_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    invalidate_module_db_cache(module, tenant_id)


def mutate_module_db(
    module: str,
    tenant_id: str,
    empty: dict[str, Any],
    mutator: Callable[[dict[str, Any]], Any],
) -> Any:
    with _lock:
        data = load_module_db(module, tenant_id, empty)
        result = mutator(data)
        save_module_db(module, tenant_id, data)
        return result
