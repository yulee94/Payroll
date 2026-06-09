"""Bitween API surface routing contract.

The production gateway must keep web admin, mobile app, public customer, and
internal admin traffic as separate API surfaces.  The mobile app surface uses
plain versioned app paths such as ``/api/v1/login`` so iOS/Android clients can
move from v1 to v2 without changing the whole server stack.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

API_SURFACE_ORDER = (
    "web_admin",
    "mobile_app",
    "public_customer",
    "internal_admin",
)

_API_SURFACES: dict[str, dict[str, Any]] = {
    "web_admin": {
        "id": "web_admin",
        "name": "Web Admin API",
        "audience": "Admin web frontend",
        "gateway_host": "admin-api.bitween.example",
        "base_path_template": "/api/admin/{version}",
        "exposure": "authenticated_web_admin",
        "auth": "session_or_admin_token_mfa",
        "notes": "관리자 웹 화면 전용 API. 모바일 앱 토큰과 쿠키/권한 정책을 공유하지 않는다.",
    },
    "mobile_app": {
        "id": "mobile_app",
        "name": "Mobile App API",
        "audience": "React Native iOS/Android employee app",
        "gateway_host": "mobile-api.bitween.example",
        "base_path_template": "/api/{version}",
        "supported_versions": ["v1", "v2"],
        "exposure": "employee_mobile_only",
        "auth": "bearer_token_device_binding",
        "versioned_examples": [
            "/api/v1/login",
            "/api/v1/branches",
            "/api/v1/tasks",
            "/api/v2/tasks",
        ],
        "notes": "앱 API는 반드시 버전 경로를 사용하고, 기기 식별·권한·branch_id 검사를 통과해야 한다.",
    },
    "public_customer": {
        "id": "public_customer",
        "name": "Public Customer API",
        "audience": "External customer/partner integrations",
        "gateway_host": "public-api.bitween.example",
        "base_path_template": "/api/public/{version}",
        "exposure": "internet_public_rate_limited",
        "auth": "api_key_or_oauth_client",
        "notes": "외부 고객/협력사 연동 전용. 내부 관리자 기능과 직원 개인정보 API를 노출하지 않는다.",
    },
    "internal_admin": {
        "id": "internal_admin",
        "name": "Internal Admin API",
        "audience": "Operations, batch, security, internal tooling",
        "gateway_host": "internal-api.bitween.local",
        "base_path_template": "/api/internal/{version}",
        "exposure": "private_subnet_only",
        "auth": "service_identity_mfa_breakglass",
        "notes": "운영·배치·보안관제용 내부 API. 외부 인터넷에 공개하지 않는다.",
    },
}


def api_surface_contract() -> dict[str, Any]:
    """Return a JSON-serializable API surface contract."""

    surfaces = {key: deepcopy(_API_SURFACES[key]) for key in API_SURFACE_ORDER}
    return {
        "version": "2026-06-09",
        "routing_principle": "separate_gateway_surface_then_versioned_resource_path",
        "surfaces": surfaces,
        "required_surfaces": [surfaces[key]["name"] for key in API_SURFACE_ORDER],
    }


def api_surface(surface_id: str) -> dict[str, Any]:
    """Return one surface definition by stable id."""

    sid = str(surface_id or "").strip()
    if sid not in _API_SURFACES:
        raise KeyError(f"unknown API surface: {surface_id}")
    return deepcopy(_API_SURFACES[sid])


def build_api_path(surface_id: str, path: str, *, version: str = "v1") -> str:
    """Build a versioned route path for one API surface.

    ``path`` can be passed with or without a leading slash.  For the mobile app
    surface, ``build_api_path("mobile_app", "login", version="v1")`` returns
    ``/api/v1/login``.
    """

    surface = api_surface(surface_id)
    ver = str(version or "v1").strip()
    if not ver.startswith("v"):
        ver = f"v{ver}"
    clean = str(path or "").strip()
    if not clean.startswith("/"):
        clean = f"/{clean}"
    base = str(surface["base_path_template"]).format(version=ver).rstrip("/")
    return f"{base}{clean}"
