"""core/labels.py - 파일·문서 표시 이름 (경로·확장자 숨김)"""

from __future__ import annotations

import re
from pathlib import Path

_FILE_LABELS: dict[str, str] = {
    "급여대장.xlsx": "급여대장",
    "급여명세서.xlsx": "급여명세서",
    "지급내역.xlsx": "지급내역",
    "payroll_snapshot.json": "급여 현황 데이터",
    "연차사용대장.xlsx": "연차사용대장",
}


def label_for_filename(name: str) -> str:
    base = Path(name).name
    if base in _FILE_LABELS:
        return _FILE_LABELS[base]
    if base.startswith("급여대장_추가"):
        return "급여대장 (추가)"
    if "전월대비" in base and "급여" in base:
        return "전월 대비 급여차이 보고"
    if "급여스냅샷" in base:
        return "급여 스냅샷"
    if "월별요약" in base:
        return "월별 요약 보고"
    stem = Path(base).stem
    stem = re.sub(r"_\d+$", "", stem)
    return stem.replace("_", " ")
