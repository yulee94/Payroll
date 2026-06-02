"""
logger_util.py - 처리 로그 기록

output/logs/ 폴더에 일별 로그 파일을 남깁니다.
오류 추적·감사(Audit)용으로 사용합니다.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "output" / "logs"

_logger: logging.Logger | None = None


def get_logger() -> logging.Logger:
    """앱 전역 로거 (최초 1회만 파일 핸들러 설정)."""
    global _logger
    if _logger is not None:
        return _logger

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"payroll_{datetime.now():%Y%m%d}.log"

    logger = logging.getLogger("payroll")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    _logger = logger
    return logger
