"""
services/payroll_ai_context.py - 급여·인사 데이터 조회 (AI 컨텍스트용)
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from core.access_control import (
    build_month_summary_secured,
    load_payroll_records_secured,
)
from core.session_service import UserSession
from core.tenant_data_scope import (
    enforce_session_tenant_access,
    list_periods_for_tenant,
    tenant_data_scope_label,
)
from payroll_archive import _period_sort_key, format_period_display
from roster_constants import find_fuzzy_name_key, norm_name_key

_PERIOD_YM = re.compile(r"(20\d{2})[-/년.\s]*(\d{1,2})")
_MONTH_ONLY = re.compile(r"(\d{1,2})\s*월")
_KOR_TOKEN = re.compile(r"[가-힣A-Za-z]{2,10}")
_WORKPLACE_PREFIXES = ("한국", "(주)", "주식회사")
_SKIP_NAMES = frozenset(
    {
        "급여",
        "월별",
        "전월",
        "당월",
        "명부",
        "직원",
        "근로자",
        "총액",
        "합계",
        "인원",
        "총급여",
        "월급",
        "임금",
        "실수령",
        "공제",
        "명세",
        "지급",
        "내역",
        "요약",
        "알려",
        "알려줘",
        "보여",
        "보여줘",
    }
)
_NAME_PATTERNS = (
    re.compile(r"(?:\d{1,2}\s*월\s+)?([가-힣]{2,4})\s*(?:님|씨)?\s*의?\s*급여"),
    re.compile(r"([가-힣]{2,4})\s*(?:님|씨)?\s*의?\s*(?:급여|월급|임금|실수령|총급여)"),
    re.compile(r"(?:\d{1,2}\s*월\s+)([가-힣]{2,4})"),
    re.compile(r"([가-힣]{2,4})\s*(?:님|씨)?\s*의?\s*(?:혜택|지원|지원사업|국가지원|프로그램)"),
)


def _won(n: int | float) -> str:
    return f"{int(n):,}원"


def _norm_workplace_key(text: str) -> str:
    """사업장명 비교용 — 공백 제거, 앰/엠 표기 통일."""
    s = norm_name_key(text).lower()
    return s.replace("앰", "엠")


def _workplace_candidates_for_tenant(tenant_id: str) -> dict[str, set[str]]:
    """대표 사업장명 → 검색 가능한 모든 표기·별칭."""
    from core.org_config import (
        all_names_for_scope_workplace,
        canonical_scope_workplace,
        list_config_workplaces,
    )
    from core.tenant_data_scope import discover_scopes_for_tenant

    out: dict[str, set[str]] = {}

    for canon in list_config_workplaces():
        bucket = out.setdefault(canon, set())
        bucket.update(all_names_for_scope_workplace(canon))

    for scope in discover_scopes_for_tenant(tenant_id):
        canon = canonical_scope_workplace(scope.workplace)
        bucket = out.setdefault(canon, set())
        bucket.add(scope.workplace)
        bucket.update(all_names_for_scope_workplace(canon))

    for canon, names in list(out.items()):
        for name in list(names):
            nn = _norm_workplace_key(name)
            for prefix in _WORKPLACE_PREFIXES:
                p = _norm_workplace_key(prefix)
                if nn.startswith(p) and len(nn) > len(p) + 1:
                    out[canon].add(name[len(prefix) :].strip() or name)
                    out[canon].add(nn[len(p) :])
    return out


def _token_matches_workplace(token: str, name: str) -> bool:
    t = _norm_workplace_key(token)
    n = _norm_workplace_key(name)
    if len(t) < 2:
        return False
    if t == n or t in n or n.endswith(t):
        return True
    for prefix in _WORKPLACE_PREFIXES:
        p = _norm_workplace_key(prefix)
        if n.startswith(p):
            tail = n[len(p) :]
            if t == tail or tail.startswith(t) or t in tail:
                return True
    return False


def extract_workplace_from_text(text: str, tenant_id: str) -> str | None:
    """
    질문에서 사업장(근무지) 힌트를 추출합니다.
    예: '5월 엠코 급여' → '한국앰코'
    """
    candidates = _workplace_candidates_for_tenant(tenant_id)
    if not candidates:
        return None

    t = str(text or "")
    qnorm = _norm_workplace_key(t)
    best_canon: str | None = None
    best_score = 0

    for canon, names in candidates.items():
        for name in names:
            nn = _norm_workplace_key(name)
            if len(nn) < 2:
                continue
            if nn in qnorm:
                score = len(nn) + 10
                if score > best_score:
                    best_score = score
                    best_canon = canon

    for raw_token in _KOR_TOKEN.findall(t):
        token = raw_token.strip()
        if token in _SKIP_NAMES or re.fullmatch(r"\d+월?", token):
            continue
        for canon, names in candidates.items():
            if any(_token_matches_workplace(token, name) for name in names):
                score = len(_norm_workplace_key(token))
                if score > best_score:
                    best_score = score
                    best_canon = canon

    return best_canon


def list_available_periods(tenant_id: str) -> list[str]:
    return list_periods_for_tenant(tenant_id)


def parse_period_from_text(text: str, available: list[str] | None = None) -> str | None:
    if not available:
        return None
    t = str(text or "")
    m = _PERIOD_YM.search(t)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        cand = f"{y:04d}-{mo:02d}"
        if cand in available:
            return cand
        for p in available:
            if p.endswith(f"-{mo:02d}") and p.startswith(str(y)):
                return p
    m2 = _MONTH_ONLY.search(t)
    if m2:
        mo = int(m2.group(1))
        today = date.today()
        candidates = [p for p in available if p.endswith(f"-{mo:02d}")]
        if not candidates:
            return None
        year_pref = today.year
        ym = f"{year_pref:04d}-{mo:02d}"
        if ym in candidates:
            return ym
        return sorted(candidates, key=_period_sort_key, reverse=True)[0]
    return None


def _person_name_conflicts_with_workplace(name: str | None, workplace: str | None) -> bool:
    if not name or not workplace:
        return False
    from core.org_config import all_names_for_scope_workplace

    names = set(all_names_for_scope_workplace(workplace))
    names.add(workplace)
    return any(_token_matches_workplace(name, n) for n in names)


def extract_person_name(text: str, *, exclude: frozenset[str] | None = None) -> str | None:
    t = str(text or "").strip()
    excluded = {_norm_workplace_key(x) for x in (exclude or frozenset()) if x}
    for pat in _NAME_PATTERNS:
        m = pat.search(t)
        if not m:
            continue
        name = re.sub(r"(의|이|가)$", "", m.group(1).strip())
        if len(name) >= 2 and name not in _SKIP_NAMES:
            if _norm_workplace_key(name) in excluded:
                continue
            return name
    return None


def _filter_records_by_workplace(
    records: list[dict[str, Any]],
    canonical_workplace: str,
) -> list[dict[str, Any]]:
    from core.org_config import all_names_for_scope_workplace, scope_workplaces_match

    names = all_names_for_scope_workplace(canonical_workplace)
    out: list[dict[str, Any]] = []
    for rec in records:
        scope_wp = str(rec.get("_scope_workplace") or "").strip()
        row_wp = str(rec.get("workplace") or "").strip()
        if scope_wp and scope_workplaces_match(canonical_workplace, scope_wp):
            out.append(rec)
        elif row_wp and (row_wp in names or scope_workplaces_match(canonical_workplace, row_wp)):
            out.append(rec)
    return out


def _summarize_records(records: list[dict[str, Any]]) -> tuple[int, int, int, int]:
    total_gross = sum(int(r.get("gross_pay") or 0) for r in records)
    total_net = sum(int(r.get("net_pay") or 0) for r in records)
    total_deduction = sum(int(r.get("total_deduction") or 0) for r in records)
    return len(records), total_gross, total_net, total_deduction


def _match_records_by_name(records: list[dict[str, Any]], name: str) -> list[dict[str, Any]]:
    if not name:
        return []
    key = norm_name_key(name)
    keys = {norm_name_key(r.get("name")) for r in records if r.get("name")}
    fuzzy = find_fuzzy_name_key(key, keys)
    if fuzzy:
        return [r for r in records if norm_name_key(r.get("name")) == fuzzy]
    exact = [r for r in records if norm_name_key(r.get("name")) == key]
    if exact:
        return exact
    partial = [r for r in records if name in str(r.get("name") or "")]
    return partial


def format_employee_payroll_line(rec: dict[str, Any], period: str) -> str:
    wp = rec.get("_scope_workplace") or rec.get("workplace") or ""
    aff = rec.get("affiliate") or ""
    scope = f" ({aff} · {wp})" if wp or aff else ""
    return (
        f"- {rec.get('name', '')}{scope} / {format_period_display(period)}\n"
        f"  총지급(세전): {_won(rec.get('gross_pay') or 0)}, "
        f"실수령: {_won(rec.get('net_pay') or 0)}, "
        f"공제합계: {_won(rec.get('total_deduction') or 0)}\n"
        f"  기본급: {_won(rec.get('base_salary') or 0)}, "
        f"연장: {_won(rec.get('ot_pay') or 0)}, "
        f"특근: {_won(rec.get('special_pay') or 0)}, "
        f"교통비: {_won(rec.get('transport') or 0)}"
    )


def build_payroll_context(
    question: str,
    tenant_id: str,
    *,
    session: UserSession | None = None,
) -> tuple[str, str | None]:
    """
    질문에 맞는 로컬 급여 데이터 컨텍스트 생성 (해당 고객사·법인만).

    Returns:
        (context_for_llm, direct_answer_if_confident)
    """
    sess = enforce_session_tenant_access(session) if session is not None else None
    tid = str(tenant_id).strip()
    periods = list_available_periods(tid)
    period = parse_period_from_text(question, periods)
    workplace = extract_workplace_from_text(question, tid)
    name = extract_person_name(question)
    if _person_name_conflicts_with_workplace(name, workplace):
        name = None
    scope_label = tenant_data_scope_label(tid)

    lines: list[str] = [
        "=== Bitween 로컬 급여 데이터 (본인 고객사 법인만) ===",
        f"데이터 범위(계열사): {scope_label}",
        f"사용 가능한 급여월: {', '.join(format_period_display(p) for p in periods[:12]) or '없음'}",
    ]
    if workplace:
        lines.append(f"인식한 사업장: {workplace}")

    direct: str | None = None

    if period and workplace and name:
        records = load_payroll_records_secured(period, tid, session=sess)
        site_records = _filter_records_by_workplace(records, workplace)
        matches = _match_records_by_name(site_records, name)
        if not site_records:
            lines.append(
                f"\n[{format_period_display(period)} · {workplace}] "
                f"저장된 급여 스냅샷이 없습니다."
            )
        elif len(matches) == 1:
            rec = matches[0]
            block = format_employee_payroll_line(rec, period)
            lines.append(
                f"\n[조회 결과 — {name} / {workplace} / {format_period_display(period)}]\n{block}"
            )
            direct = (
                f"{workplace} {name} 님의 {format_period_display(period)} 급여는 "
                f"총지급 {_won(rec.get('gross_pay') or 0)}, "
                f"실수령 {_won(rec.get('net_pay') or 0)} 입니다."
            )
        elif len(matches) > 1:
            lines.append(f"\n[{workplace} · {name}] 동명/유사 인원 {len(matches)}명:")
            for rec in matches:
                lines.append(format_employee_payroll_line(rec, period))
        else:
            lines.append(
                f"\n[{format_period_display(period)} · {workplace}] "
                f"'{name}' 을(를) 찾지 못했습니다."
            )

    elif period and workplace:
        records = load_payroll_records_secured(period, tid, session=sess)
        filtered = _filter_records_by_workplace(records, workplace)
        if not filtered:
            lines.append(
                f"\n[{format_period_display(period)} · {workplace}] "
                f"저장된 급여 스냅샷이 없습니다."
            )
        else:
            count, gross, net, deduction = _summarize_records(filtered)
            lines.append(
                f"\n[{format_period_display(period)} · {workplace} 요약] "
                f"인원 {count}명, "
                f"총지급 합계 {_won(gross)}, "
                f"실수령 합계 {_won(net)}, "
                f"공제 합계 {_won(deduction)}"
            )
            top = sorted(filtered, key=lambda r: int(r.get("gross_pay") or 0), reverse=True)[:5]
            if top:
                lines.append("총지급 상위 5명:")
                for r in top:
                    lines.append(
                        f"  · {r.get('name')}: {_won(r.get('gross_pay') or 0)} "
                        f"(실수령 {_won(r.get('net_pay') or 0)})"
                    )
            direct = (
                f"{workplace} {format_period_display(period)} 급여는 "
                f"인원 {count}명, 총지급 {_won(gross)}, 실수령 {_won(net)} 입니다."
            )

    elif period and name:
        records = load_payroll_records_secured(period, tid, session=sess)
        matches = _match_records_by_name(records, name)
        if not records:
            lines.append(
                f"\n[{format_period_display(period)}] 이 법인({scope_label})에 저장된 급여 스냅샷이 없습니다."
            )
        elif len(matches) == 1:
            rec = matches[0]
            block = format_employee_payroll_line(rec, period)
            lines.append(f"\n[조회 결과 — {name} / {format_period_display(period)}]\n{block}")
            direct = (
                f"{name} 님의 {format_period_display(period)} 급여는 "
                f"총지급 {_won(rec.get('gross_pay') or 0)}, "
                f"실수령 {_won(rec.get('net_pay') or 0)} 입니다."
            )
        elif len(matches) > 1:
            lines.append(f"\n[{name}] 동명/유사 인원 {len(matches)}명 — 사업장별:")
            for rec in matches:
                lines.append(format_employee_payroll_line(rec, period))
            direct = (
                f"{name} 님은 {format_period_display(period)}에 {len(matches)}건(사업장별)이 있습니다. "
                "자세한 내역은 아래 컨텍스트를 참고하세요."
            )
        else:
            lines.append(f"\n[{format_period_display(period)}] '{name}' 을(를) 찾지 못했습니다.")
            names = sorted({str(r.get("name") or "") for r in records if r.get("name")})[:30]
            lines.append("해당 월 인원 예시: " + ", ".join(names))

    elif period:
        summary = build_month_summary_secured(period, tid, session=sess)
        records = load_payroll_records_secured(period, tid, session=sess)
        lines.append(
            f"\n[{format_period_display(period)} 요약] "
            f"인원 {summary.employee_count}명, "
            f"총지급 합계 {_won(summary.total_gross)}, "
            f"실수령 합계 {_won(summary.total_net)}"
        )
        top = sorted(records, key=lambda r: int(r.get("gross_pay") or 0), reverse=True)[:5]
        if top:
            lines.append("총지급 상위 5명:")
            for r in top:
                lines.append(
                    f"  · {r.get('name')}: {_won(r.get('gross_pay') or 0)} (실수령 {_won(r.get('net_pay') or 0)})"
                )

    elif workplace:
        lines.append(f"\n[{workplace} 최근 급여 검색]")
        found_any = False
        for p in periods[:6]:
            recs = _filter_records_by_workplace(
                load_payroll_records_secured(p, tid, session=sess),
                workplace,
            )
            if recs:
                found_any = True
                count, gross, net, _ = _summarize_records(recs)
                lines.append(
                    f"  · {format_period_display(p)}: 인원 {count}명, "
                    f"총지급 {_won(gross)}, 실수령 {_won(net)}"
                )
        if not found_any:
            lines.append("최근 6개월 내 스냅샷에서 찾지 못했습니다.")

    elif name:
        lines.append(f"\n[이름 '{name}' 최근 급여 검색]")
        found_any = False
        for p in periods[:6]:
            recs = _match_records_by_name(load_payroll_records_secured(p, tid, session=sess), name)
            if recs:
                found_any = True
                for rec in recs:
                    lines.append(format_employee_payroll_line(rec, p))
        if not found_any:
            lines.append("최근 6개월 내 스냅샷에서 찾지 못했습니다.")

    else:
        if periods:
            latest = periods[0]
            summary = build_month_summary_secured(latest, tid, session=sess)
            lines.append(
                f"\n[최근 급여월 {format_period_display(latest)}] "
                f"인원 {summary.employee_count}명, 총지급 {_won(summary.total_gross)}"
            )

    lines.append(
        "\n안내: 위 데이터는 로그인한 고객사 법인만 포함합니다. "
        "타 법인 급여는 제공·추측하지 마세요. 없는 수치는 추측하지 마세요."
    )
    return "\n".join(lines), direct


def build_payroll_context_for_session(
    question: str,
    session=None,
) -> tuple[str, str | None]:
    from core.session_service import require_session

    sess = enforce_session_tenant_access(session or require_session())
    return build_payroll_context(question, sess.tenant_id, session=sess)