"""
validator.py - 급여 처리 전·후 검증

누락 직원, 음수 금액, 계좌번호 미등록 등을 사전에 경고합니다.
"""

from __future__ import annotations

from typing import Any


class PayrollValidationError(Exception):
    """검증 실패 시 발생 (차단 수준)."""

    def __init__(self, messages: list[str]) -> None:
        self.messages = messages
        super().__init__("\n".join(messages))


def validate_invoice_rows(rows: list[dict[str, Any]]) -> list[str]:
    """
    청구서 추출 직후 검증.

    Returns:
        경고 메시지 목록 (비어 있으면 OK)
    """
    warnings: list[str] = []
    if not rows:
        raise PayrollValidationError(["청구서에 직원 정보가 없습니다. 양식을 확인해 주세요."])

    for row in rows:
        name = str(row.get("name", "")).strip()
        if not name:
            warnings.append("이름이 비어 있는 행이 있습니다.")
    return warnings


def validate_results(results: list[dict[str, Any]]) -> list[str]:
    """계산 결과 검증 (선택)."""
    warnings: list[str] = []
    for r in results:
        name = r.get("name", "?")
        if r.get("net_pay", 0) < 0:
            warnings.append(f"[{name}] 실수령액이 음수입니다.")
        if not r.get("account"):
            warnings.append(f"{name}: 계좌번호가 없습니다. 명부 또는 지급내역 양식에 등록이 필요합니다.")
        holder = str(r.get("holder") or "").strip()
        emp_name = str(name or "").strip()
        if holder and emp_name and holder.replace(" ", "") != emp_name.replace(" ", ""):
            warnings.append(
                f"{name}: 예금주가 근로자 성명({emp_name})과 다릅니다 — "
                f"지급 예금주「{holder}」로 이체합니다."
            )
    return warnings
