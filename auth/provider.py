"""
auth/provider.py - 사원번호·비밀번호 로그인 (예정)

향후 회원가입·배포 시 LocalAuthProvider / RemoteAuthProvider 로 교체.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class UserSession:
    emp_no: str
    name: str
    role: str = "staff"


class AuthProvider(Protocol):
    def login(self, emp_no: str, password: str) -> UserSession | None:
        ...

    def logout(self) -> None:
        ...


class NoAuthProvider:
    """현재: 로그인 없이 로컬 단일 사용자."""

    _session: UserSession | None = None

    def login(self, emp_no: str, password: str) -> UserSession | None:
        _ = password
        self._session = UserSession(emp_no=emp_no or "admin", name="관리자", role="admin")
        return self._session

    def logout(self) -> None:
        self._session = None

    @property
    def current(self) -> UserSession | None:
        return self._session


def get_auth_provider() -> AuthProvider:
    from core.config import APP_CONFIG

    if APP_CONFIG.auth_enabled:
        # return DatabaseAuthProvider(...)
        pass
    return NoAuthProvider()
