#!/usr/bin/env python3
"""Generate Direction C Open Graph cards (1200×630) — Signal over noise."""

from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "og"
FONTS = Path(__file__).resolve().parent / "fonts"

INK = (15, 23, 36)  # #0F1724
PAPER = (243, 242, 238)  # #F3F2EE
TEAL = (107, 191, 174)  # #6BBFAE
META = (160, 168, 176)
NOISE = (90, 100, 112)

W, H = 1200, 630


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = FONTS / name
    if not path.exists():
        # Fallbacks
        alts = {
            "SourceSerif4-Semibold.ttf": "/tmp/SourceSerif4-Semibold.ttf",
            "SourceSerif4-It.ttf": "/tmp/SourceSerif4-It.ttf",
            "IBMPlexMono-Regular.ttf": "/usr/share/fonts/truetype/ibm-plex/IBMPlexMono-Regular.ttf",
            "IBMPlexMono-Light.ttf": "/usr/share/fonts/truetype/ibm-plex/IBMPlexMono-Light.ttf",
        }
        path = Path(alts.get(name, str(path)))
    return ImageFont.truetype(str(path), size)


def noise_polyline(
    x0: float, x1: float, y: float, amp: float = 3.2, step: float = 7.0, seed: int = 7
) -> list[tuple[float, float]]:
    rng = random.Random(seed)
    pts = []
    x = x0
    while x <= x1:
        pts.append((x, y + rng.uniform(-amp, amp)))
        x += step
    if pts[-1][0] < x1:
        pts.append((x1, y + rng.uniform(-amp, amp)))
    return pts


def draw_signal_line(d: ImageDraw.ImageDraw, y: float = 520) -> None:
    """Long noise → n-pulse (right third) → flat → teal dot."""
    left = 72
    right = W - 72
    pulse_start = 780
    pulse_end = 980
    flat_end = right - 28

    # Noise before pulse
    pts = noise_polyline(left, pulse_start, y, amp=2.8, step=6.5, seed=11)
    d.line(pts, fill=NOISE, width=2, joint="curve")

    # n-pulse as rounded arch (paper, thicker)
    # feet + stems + arch
    n_left = pulse_start + 8
    n_right = pulse_end - 40
    arch_top = y - 78
    # left foot into stem
    path = [
        (pulse_start, y),
        (n_left, y),
        (n_left, y - 8),
    ]
    # Use arc approximation with many points
    cx = (n_left + n_right) / 2
    rx = (n_right - n_left) / 2
    ry = y - 8 - arch_top
    for i in range(0, 33):
        t = math.pi * (1 - i / 32)  # π → 0 (left stem top → right stem top via top)
        # Actually go from left base up: start at bottom left of arch
        pass
    # Cleaner: cubic via points
    arch = []
    for i in range(0, 41):
        t = i / 40
        # parametric: go up left stem, over arch, down right stem
        if t < 0.18:
            u = t / 0.18
            arch.append((n_left, y - u * (y - arch_top - 4)))
        elif t < 0.82:
            u = (t - 0.18) / 0.64
            ang = math.pi * (1 - u)  # π → 0
            arch.append((cx + rx * math.cos(ang), arch_top + ry * (1 - math.sin(ang))))
        else:
            u = (t - 0.82) / 0.18
            arch.append((n_right, arch_top + 4 + u * (y - arch_top - 4)))
    # lead-in from noise end
    d.line([(pulse_start, y), (n_left, y), *arch, (n_right + 8, y), (flat_end, y)], fill=PAPER, width=4)
    # Soften join: redraw arch thicker alone
    d.line([(n_left, y), *arch, (n_right, y)], fill=PAPER, width=5, joint="curve")
    d.line([(n_right, y), (flat_end, y)], fill=PAPER, width=3)

    # Teal signal dot
    r = 7
    d.ellipse([flat_end - r, y - r, flat_end + r, y + r], fill=TEAL)


def draw_tracked(d: ImageDraw.ImageDraw, xy: tuple[float, float], text: str, font_obj, fill, tracking: float = 3.5, anchor: str = "lt") -> None:
    """Draw uppercase mono with letter-spacing."""
    x, y = xy
    widths = []
    for ch in text:
        bbox = d.textbbox((0, 0), ch, font=font_obj)
        widths.append(bbox[2] - bbox[0])
    total = sum(widths) + tracking * max(0, len(text) - 1)
    if anchor == "rt":
        x = x - total
    elif anchor == "mt":
        x = x - total / 2
    for ch, w in zip(text, widths):
        d.text((x, y), ch, font=font_obj, fill=fill)
        x += w + tracking


def draw_card(
    path: Path,
    top_left: str,
    top_right: str,
    tagline: str,
) -> None:
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)

    mono = font("IBMPlexMono-Regular.ttf", 17)
    # Top meta (tracked)
    draw_tracked(d, (72, 56), top_left, mono, META, tracking=3.2)
    draw_tracked(d, (W - 72, 56), top_right, mono, META, tracking=3.2, anchor="rt")

    # Centered wordmark
    brand = font("SourceSerif4-Semibold.ttf", 72)
    word = "newsletter"
    tld = ".si"
    wb = d.textbbox((0, 0), word, font=brand)
    tb = d.textbbox((0, 0), tld, font=brand)
    total_w = (wb[2] - wb[0]) + (tb[2] - tb[0])
    x0 = (W - total_w) / 2
    y_brand = 250
    d.text((x0, y_brand), word, font=brand, fill=PAPER, anchor="lt")
    d.text((x0 + (wb[2] - wb[0]), y_brand), tld, font=brand, fill=TEAL, anchor="lt")

    # Italic tagline under wordmark
    italic = font("SourceSerif4-It.ttf", 28)
    d.text((W / 2, 340), tagline, font=italic, fill=PAPER, anchor="mt")

    draw_signal_line(d, y=520)

    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG", optimize=True)
    assert path.stat().st_size < 300_000, path.stat().st_size
    print(f"{path.name}: {path.stat().st_size} bytes")


def main() -> None:
    cards = [
        (
            "default.png",
            "DAILY · 08:25 AEST",
            "MARKETS / AI",
            "Signal over noise. The few things that matter today.",
        ),
        (
            "markets.png",
            "DAILY · 08:25 AEST",
            "MARKETS",
            "ASX · Macro · Oil · Gold",
        ),
        (
            "ai.png",
            "DAILY · 08:25 AEST",
            "AI",
            "Coding agents · Evals · Models · Papers",
        ),
        (
            "archive.png",
            "ARCHIVE",
            "MARKETS / AI",
            "Past issues. Still signal.",
        ),
    ]
    for name, left, right, tagline in cards:
        draw_card(OUT / name, left, right, tagline)
    print("done", OUT)


if __name__ == "__main__":
    main()
