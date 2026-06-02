"""
ui/kpi_map_assets.py - KPI 경영 지도 배경 (대한민국 행정지도 PNG)
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageTk

from core.paths import app_data_dir, app_install_dir, bundle_dir, dev_root, is_frozen

# 지역 핀 좌표 (지도 이미지 기준 0~1)
MAP_PIN_ORIGIN = (0.0, 0.0)
MAP_PIN_SIZE = (1.0, 1.0)

KOREA_MAINLAND: tuple[tuple[float, float], ...] = (
    (0.382, 0.042),
    (0.445, 0.035),
    (0.520, 0.038),
    (0.598, 0.055),
    (0.652, 0.120),
    (0.685, 0.200),
    (0.710, 0.280),
    (0.725, 0.360),
    (0.735, 0.440),
    (0.748, 0.520),
    (0.720, 0.565),
    (0.650, 0.590),
    (0.580, 0.600),
    (0.500, 0.595),
    (0.420, 0.580),
    (0.360, 0.520),
    (0.320, 0.440),
    (0.300, 0.360),
    (0.285, 0.280),
    (0.295, 0.200),
    (0.320, 0.120),
    (0.350, 0.070),
)

JEJU_CENTER = (0.235, 0.885)
JEJU_RX = 0.045
JEJU_RY = 0.028


_KOREA_MAP_REL = Path("assets") / "korea_map.png"


def _bundled_map_candidates() -> list[Path]:
    """읽기 전용 번들·설치·개발 경로 (우선순위 순)."""
    roots: list[Path] = []
    bundled = bundle_dir()
    if bundled is not None:
        roots.append(bundled)
    if is_frozen():
        roots.append(app_install_dir())
    roots.append(dev_root())
    return [root / _KOREA_MAP_REL for root in roots]


def _writable_map_path() -> Path:
    """생성·캐시 PNG 저장 경로 (쓰기 가능)."""
    if is_frozen():
        return app_data_dir() / "cache" / "assets" / "korea_map.png"
    return dev_root() / _KOREA_MAP_REL


def _find_readable_map() -> Path | None:
    for candidate in _bundled_map_candidates():
        if candidate.is_file():
            return candidate
    cached = _writable_map_path()
    if cached.is_file():
        return cached
    return None


def _scale_points(
    points: tuple[tuple[float, float], ...],
    *,
    width: int,
    height: int,
    pad_x: int,
    pad_y: int,
) -> list[tuple[int, int]]:
    inner_w = width - pad_x * 2
    inner_h = height - pad_y * 2
    return [(pad_x + int(x * inner_w), pad_y + int(y * inner_h)) for x, y in points]


def generate_korea_map_png(path: Path, *, width: int = 820, height: int = 980) -> None:
    """대한민국 윤곽 지도 PNG 생성 (오프라인·배포용)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    ocean = (238, 244, 255, 255)
    land = (196, 214, 236, 255)
    land_inner = (210, 228, 248, 255)
    border = (100, 116, 139, 255)
    coast = (148, 163, 184, 180)

    img = Image.new("RGBA", (width, height), ocean)
    draw = ImageDraw.Draw(img)

    pad_x, pad_y = 48, 56
    mainland = _scale_points(KOREA_MAINLAND, width=width, height=height, pad_x=pad_x, pad_y=pad_y)
    draw.polygon(mainland, fill=land_inner, outline=border, width=3)

    jx = pad_x + int(JEJU_CENTER[0] * (width - pad_x * 2))
    jy = pad_y + int(JEJU_CENTER[1] * (height - pad_y * 2))
    jrx = int(JEJU_RX * (width - pad_x * 2))
    jry = int(JEJU_RY * (height - pad_y * 2))
    draw.ellipse((jx - jrx, jy - jry, jx + jrx, jy + jry), fill=land_inner, outline=border, width=2)

    try:
        font = ImageFont.truetype("malgun.ttf", 15)
        font_sm = ImageFont.truetype("malgun.ttf", 11)
    except OSError:
        font = ImageFont.load_default()
        font_sm = font

    draw.text((width // 2, 18), "대한민국", fill=(71, 85, 105, 255), font=font, anchor="mm")
    draw.text((jx, jy + jry + 14), "제주", fill=(100, 116, 139, 255), font=font_sm, anchor="mm")

    labels = (
        ("서울·수도권", 0.48, 0.28),
        ("강원", 0.55, 0.20),
        ("경기·인천", 0.35, 0.34),
        ("충청", 0.42, 0.52),
        ("경북·대구", 0.60, 0.58),
        ("부산·경남", 0.74, 0.80),
        ("전라", 0.34, 0.72),
    )
    for text, lx, ly in labels:
        tx = pad_x + int(lx * (width - pad_x * 2))
        ty = pad_y + int(ly * (height - pad_y * 2))
        draw.text((tx, ty), text, fill=(148, 163, 184, 200), font=font_sm, anchor="mm")

    rgb = Image.new("RGB", img.size, ocean[:3])
    rgb.paste(img, mask=img.split()[3])
    rgb.save(path, format="PNG", optimize=True)


def ensure_korea_map_image() -> Path:
    existing = _find_readable_map()
    if existing is not None:
        return existing
    path = _writable_map_path()
    generate_korea_map_png(path)
    return path


def load_korea_map_photo(master: tk.Misc, *, max_width: int, max_height: int) -> tuple[tk.PhotoImage | None, int, int]:
    """캔버스 크기에 맞춘 PhotoImage 와 (width, height) 반환."""
    path = ensure_korea_map_image()
    try:
        src = Image.open(path).convert("RGBA")
    except OSError:
        return None, 0, 0

    scale = min(max_width / src.width, max_height / src.height)
    if scale <= 0:
        return None, 0, 0
    nw = max(1, int(src.width * scale))
    nh = max(1, int(src.height * scale))
    resized = src.resize((nw, nh), Image.Resampling.LANCZOS)
    photo = ImageTk.PhotoImage(resized, master=master)
    return photo, nw, nh


def map_content_rect(canvas_w: int, canvas_h: int, img_w: int, img_h: int, *, title_h: int = 28) -> tuple[int, int, int, int]:
    """지도 이미지가 그려질 (x0, y0, w, h)."""
    top = title_h
    avail_h = max(1, canvas_h - top - 8)
    avail_w = max(1, canvas_w - 16)
    scale = min(avail_w / img_w, avail_h / img_h)
    nw = int(img_w * scale)
    nh = int(img_h * scale)
    x0 = (canvas_w - nw) // 2
    y0 = top + (avail_h - nh) // 2
    return x0, y0, nw, nh


def pin_xy(map_x: float, map_y: float, x0: int, y0: int, nw: int, nh: int) -> tuple[int, int]:
    return x0 + int(float(map_x) * nw), y0 + int(float(map_y) * nh)
