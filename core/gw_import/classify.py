"""Document type inference for GW imports."""

from __future__ import annotations

from core.workflow.constants import (
    DOC_TYPE_ATTENDANCE,
    DOC_TYPE_EXPENSE,
    DOC_TYPE_GENERAL,
    DOC_TYPE_PURCHASE,
)

DEFAULT_REQUESTER = "7df8dfc8dd7d44008338ddba3365f307"


def infer_document_type(title: str) -> str:
    t = title or ""
    if any(k in t for k in ("구매", "구입", "소모품", "피복", "발주", "지급 요청")):
        return DOC_TYPE_PURCHASE
    if any(k in t for k in ("지출", "품의", "결의", "정산")):
        return DOC_TYPE_EXPENSE
    if any(k in t for k in ("연차", "휴가", "근태", "출근", "근무", "부재")):
        return DOC_TYPE_ATTENDANCE
    return DOC_TYPE_GENERAL
