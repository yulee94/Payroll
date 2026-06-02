"""
ui/brand_assets.py - 로고 합성·PhotoImage (배경별 가시성 보장)
"""

from __future__ import annotations

import os
import tempfile
import tkinter as tk
from pathlib import Path
from typing import Any, Literal

from PIL import Image

from core.config import BITWEEN_LOGO_PATH, LOGO_PATH
from core.tenant_store import resolve_company_logo_path
from ui.theme import COLORS, FONT

LogoVariant = Literal["light", "dark", "sidebar"]

_NAVY = "#1F3864"


def resolve_bitween_logo_path() -> Path:
    """Bitween 플랫폼 로고 (로그인·랜딩용, 테넌트 무관)."""
    if BITWEEN_LOGO_PATH.is_file():
        return BITWEEN_LOGO_PATH
    return LOGO_PATH


def attach_bitween_logo_label(
    parent: tk.Misc,
    refs: list[Any],
    master: tk.Misc,
    *,
    max_width: int = 200,
    variant: LogoVariant = "light",
    bg: str | None = None,
    blend_bg: str | None = None,
    **pack_kw: Any,
) -> tk.Label | None:
    """로그인·랜딩 화면용 Bitween 플랫폼 로고."""
    return attach_logo_label(
        parent,
        refs,
        master,
        max_width=max_width,
        variant=variant,
        bg=bg,
        blend_bg=blend_bg,
        logo_path=resolve_bitween_logo_path(),
        **pack_kw,
    )


def _hex_rgb(color: str) -> tuple[int, int, int]:
    c = color.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def _trim_alpha(img: Image.Image) -> Image.Image:
    if img.mode != "RGBA":
        return img.convert("RGBA")
    bbox = img.getbbox()
    if not bbox:
        return img
    return img.crop(bbox)


def _resize_max_width(img: Image.Image, max_width: int) -> Image.Image:
    if img.width <= max_width:
        return img
    ratio = max_width / img.width
    return img.resize((max_width, max(1, int(img.height * ratio))), Image.Resampling.LANCZOS)


def _recolor_logo_for_dark_hero(img: Image.Image) -> Image.Image:
    """네이비 히어로: 어두운 로고 색만 밝게 — 흰 박스 없이 로고만 보이게."""
    out = img.convert("RGBA")
    px = out.load()
    for y in range(out.height):
        for x in range(out.width):
            r, g, b, a = px[x, y]
            if a < 12:
                continue
            lum = 0.299 * r + 0.587 * g + 0.114 * b
            if b > 140 and g > 90 and r < 130:
                continue
            if lum < 165:
                px[x, y] = (255, 255, 255, a)
    return out


def composite_logo_image(
    logo_path: Path | None = None,
    *,
    max_width: int = 160,
    variant: LogoVariant = "sidebar",
    blend_bg: str | None = None,
) -> Image.Image | None:
    """
    배경에 맞게 로고 합성된 RGB 이미지 (별도 박스·패널 없음).

    - dark: 히어로 네이비와 동일 배경에 로고만 합성 (밝은 색 치환)
    - light/sidebar: 해당 화면 배경색에 직접 합성
    """
    path = logo_path or resolve_company_logo_path()
    if not path.is_file():
        return None
    try:
        src = _trim_alpha(Image.open(path).convert("RGBA"))
    except OSError:
        return None

    src = _resize_max_width(src, max(40, max_width))

    if variant == "dark":
        bg_rgb = _hex_rgb(blend_bg or _NAVY)
        logo = _recolor_logo_for_dark_hero(src)
        out = Image.new("RGB", (logo.width, logo.height), bg_rgb)
        out.paste(logo, (0, 0), logo.split()[3])
        return out
    if variant == "sidebar":
        bg = _hex_rgb(blend_bg or COLORS.get("sidebar_brand_bg", COLORS["sidebar"]))
        margin = 4
    else:
        bg = _hex_rgb(COLORS["bg"])
        margin = 4

    canvas_w = src.width + margin * 2
    canvas_h = src.height + margin * 2
    out = Image.new("RGB", (canvas_w, canvas_h), bg)
    out.paste(src, (margin, margin), src.split()[3])
    return out


def logo_photoimage(
    master: tk.Misc,
    refs: list[Any],
    *,
    max_width: int = 160,
    variant: LogoVariant = "sidebar",
    logo_path: Path | None = None,
    blend_bg: str | None = None,
) -> tk.PhotoImage | None:
    """PIL 합성 후 임시 PNG → PhotoImage (RGBA 직접 로드 금지)."""
    path = logo_path or resolve_company_logo_path()
    img = composite_logo_image(
        path, max_width=max_width, variant=variant, blend_bg=blend_bg
    )
    if img is None:
        return None

    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    fpath = tmp.name
    tmp.close()
    try:
        img.save(fpath, format="PNG")
        photo = tk.PhotoImage(file=fpath, master=master)
        refs.append(photo)
        return photo
    finally:
        try:
            os.unlink(fpath)
        except OSError:
            pass


def attach_logo_label(
    parent: tk.Misc,
    refs: list[Any],
    master: tk.Misc,
    *,
    max_width: int = 160,
    variant: LogoVariant = "sidebar",
    bg: str | None = None,
    blend_bg: str | None = None,
    logo_path: Path | None = None,
    **pack_kw: Any,
) -> tk.Label | None:
    hero_bg = blend_bg or bg
    if bg is None:
        if variant == "sidebar":
            bg = COLORS["sidebar"]
        elif variant == "dark":
            bg = hero_bg or _NAVY
        else:
            bg = COLORS["bg"]
    photo = logo_photoimage(
        master,
        refs,
        max_width=max_width,
        variant=variant,
        logo_path=logo_path,
        blend_bg=hero_bg if variant in ("dark", "sidebar") else None,
    )
    if photo is None:
        return None
    lbl = tk.Label(
        parent,
        image=photo,
        bg=bg,
        bd=0,
        highlightthickness=0,
        width=photo.width(),
        height=photo.height(),
    )
    lbl.image = photo
    lbl.pack(**pack_kw)
    return lbl
