"""법정·규정 문서 카테고리."""

from __future__ import annotations

CATEGORY_BYLAWS = "bylaws"
CATEGORY_HR_REGULATIONS = "hr_regulations"
CATEGORY_MINIMUM_WAGE = "minimum_wage"
CATEGORY_SEXUAL_HARASSMENT = "sexual_harassment_prevention"
CATEGORY_CPR_FIRST_AID = "cpr_first_aid"
CATEGORY_OTHER_STATUTORY = "other_statutory"

ALL_CATEGORIES: tuple[str, ...] = (
    CATEGORY_BYLAWS,
    CATEGORY_HR_REGULATIONS,
    CATEGORY_MINIMUM_WAGE,
    CATEGORY_SEXUAL_HARASSMENT,
    CATEGORY_CPR_FIRST_AID,
    CATEGORY_OTHER_STATUTORY,
)

CATEGORY_LABELS: dict[str, str] = {
    CATEGORY_BYLAWS: "정관",
    CATEGORY_HR_REGULATIONS: "인사규정·취업규칙",
    CATEGORY_MINIMUM_WAGE: "최저임금 공지",
    CATEGORY_SEXUAL_HARASSMENT: "성폭력 예방 교육",
    CATEGORY_CPR_FIRST_AID: "심폐소생술 교육",
    CATEGORY_OTHER_STATUTORY: "기타 법정 의무",
}

# UI 탭 그룹
TAB_GROUP_REGULATIONS = "regulations"
TAB_GROUP_STATUTORY = "statutory"

TAB_GROUP_LABELS: dict[str, str] = {
    TAB_GROUP_REGULATIONS: "정관 · 인사규정",
    TAB_GROUP_STATUTORY: "법정 의무",
}

REGULATIONS_CATEGORIES: frozenset[str] = frozenset(
    {CATEGORY_BYLAWS, CATEGORY_HR_REGULATIONS}
)

STATUTORY_CATEGORIES: frozenset[str] = frozenset(
    {
        CATEGORY_MINIMUM_WAGE,
        CATEGORY_SEXUAL_HARASSMENT,
        CATEGORY_CPR_FIRST_AID,
        CATEGORY_OTHER_STATUTORY,
    }
)

# 열람 확인(acknowledgment) 대상 — 법정 교육·공지류
ACKNOWLEDGMENT_CATEGORIES: frozenset[str] = STATUTORY_CATEGORIES

ALLOWED_EXTENSIONS: frozenset[str] = frozenset(
    {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".doc", ".docx", ".hwp", ".hwpx", ".xls", ".xlsx", ".ppt", ".pptx"}
)
