"""
ui/nav_icons.py - 사이드바 내비 아이콘 (기업용 단색 글리프)
"""

from __future__ import annotations

NAV_ITEM_ICONS: dict[str, str] = {
    "launcher": "⌂",
    "tenant": "▣",
    "permissions": "◇",
    "org": "≡",
    "group_settings": "▤",
    "ai": "✦",
    "workflow": "◎",
    "home": "₩",
    "roster": "人",
    "archive": "▥",
    "summary": "▦",
    "monthly_report": "▧",
    "reports": "▨",
    "settings": "⚙",
    "hr": "人",
    "hr_roster": "人",
    "hr_documents": "▤",
    "hr_leave": "◷",
    "hr_attendance": "◴",
    "hr_contracts": "□",
    "hr_certificates": "▢",
    "hr_labor": "§",
    "hr_onboarding": "↪",
    "recruitment": "◉",
    "recruitment_postings": "✎",
    "recruitment_marketplace": "▩",
    "recruitment_applications": "▣",
    "recruitment_channels": "⌁",
    "kpi": "▧",
    "kpi_map": "⌖",
    "kpi_entities": "▣",
    "kpi_sites": "⌾",
    "kpi_individual": "人",
    "kpi_alerts": "!",
    "maintenance": "⚙",
    "maintenance_work_orders": "▤",
    "maintenance_assets": "▣",
    "maintenance_schedules": "◷",
    "maintenance_parts": "▦",
    "bidding": "◉",
    "bidding_notices": "◉",
    "bidding_estimates": "₩",
    "bidding_submissions": "↗",
    "bidding_history": "★",
    "accounting": "▧",
    "accounting_vouchers": "▤",
    "accounting_tax_events": "◷",
    "accounting_cash_plan": "₩",
    "accounting_reports": "▨",
}

SECTION_ICONS: dict[str, str] = {
    "platform": "◆",
    "workflow": "◎",
    "payroll": "₩",
    "hr": "人",
    "recruitment": "◉",
    "kpi": "▧",
    "maintenance": "⚙",
    "bidding": "◉",
    "accounting": "▨",
}

SECTION_ACCENTS: dict[str, str] = {
    "platform": "#64748B",
    "workflow": "#2563EB",
    "payroll": "#1F3864",
    "hr": "#0D9488",
    "recruitment": "#DB2777",
    "kpi": "#4F46E5",
    "maintenance": "#0F766E",
    "bidding": "#7C3AED",
    "accounting": "#B45309",
}


def nav_item_icon(key: str) -> str:
    if key in NAV_ITEM_ICONS:
        return NAV_ITEM_ICONS[key]
    prefix = key.split("_", 1)[0]
    return NAV_ITEM_ICONS.get(prefix, "•")


def section_icon(section_id: str) -> str:
    return SECTION_ICONS.get(section_id, "▸")


def section_accent(section_id: str, *, fallback: str = "#64748B") -> str:
    return SECTION_ACCENTS.get(section_id, fallback)
