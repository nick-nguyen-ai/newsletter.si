#!/usr/bin/env python3
"""Generate SignaLetter Open Graph cards (1200×630) — Direction C share style."""

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
TEAL_MUTED = (47, 122, 117)  # #2F7A75 — sampled from brand PDF
TEAL_LIGHT = (102, 184, 172)  # #66B8AC — on dark
META = (160, 168, 176)
NOISE = (90, 100, 112)

W, H = 1200, 630


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = FONTS / name
    if not path.exists():
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


def draw_signal_mark(d: ImageDraw.ImageDraw, y: float = 520) -> None:
    """Long noise → nL signal stroke → teal dot (page-6 share card)."""
    left = 72
    right = W - 72
    mark_start = 820
    flat_end = right - 36

    # Noise before mark
    pts = noise_polyline(left, mark_start, y, amp=2.8, step=6.5, seed=11)
    d.line(pts, fill=NOISE, width=2, joint="curve")

    # nL mark scaled from 64-unit brand path into pixel space
    # Brand SIGNAL_D in 64 viewBox → map into [mark_start, flat_end] × height
    # Path: left stem, n-arch, valley, tall L peak, diagonal to teal
    x0 = mark_start
    scale_x = (flat_end - 28 - mark_start) / (56 - 15.2)
    scale_y = 3.6  # px per viewBox unit

    def X(u: float) -> float:
        return x0 + (u - 15.2) * scale_x

    def Y(v: float) -> float:
        return y + (v - 44) * scale_y

    # Approximate the SVG path with polylines for Pillow
    # Left stem + n arch
    arch = []
    # Lead-in from noise
    arch.append((X(15.2), Y(44)))
    arch.append((X(17.8), Y(44)))
    # Left stem up
    for t in range(0, 11):
        yy = 44 - (44 - 26.5) * (t / 10)
        arch.append((X(17.8), Y(yy)))
    # n-arch cubic approx: C17.8 18.8, 23.5 13.8, 30.5 13.8 then C37.2 13.8, 42 18.5, 42 26.5
    def cubic(p0, p1, p2, p3, n=24):
        out = []
        for i in range(n + 1):
            t = i / n
            u = 1 - t
            x = u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0]
            yv = u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1]
            out.append((x, yv))
        return out

    p0 = (17.8, 26.5)
    arch += cubic(p0, (17.8, 18.8), (23.5, 13.8), (30.5, 13.8))[1:]
    arch += cubic((30.5, 13.8), (37.2, 13.8), (42, 18.5), (42, 26.5))[1:]
    # Down toward valley
    for t in range(1, 11):
        yy = 26.5 + (40 - 26.5) * (t / 10)
        arch.append((42, yy))
    # Valley curve into L rise: C42 43, 43.2 44, 45 42.5 then L48 10.5 L56 37
    arch += cubic((42, 40), (42, 43), (43.2, 44), (45, 42.5))[1:]
    # Up to L peak
    for t in range(1, 16):
        xx = 45 + (48 - 45) * (t / 15)
        yy = 42.5 + (10.5 - 42.5) * (t / 15)
        arch.append((xx, yy))
    # Diagonal to teal approach
    for t in range(1, 16):
        xx = 48 + (56 - 48) * (t / 15)
        yy = 10.5 + (37 - 10.5) * (t / 15)
        arch.append((xx, yy))

    pix = [(X(x), Y(yv)) for x, yv in arch]
    d.line(pix, fill=PAPER, width=5, joint="curve")

    # Teal signal dot
    tx, ty = X(57.5), Y(38.2)
    r = 8
    d.ellipse([tx - r, ty - r, tx + r, ty + r], fill=TEAL_LIGHT)


def draw_tracked(
    d: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    font_obj,
    fill,
    tracking: float = 3.5,
    anchor: str = "lt",
) -> None:
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


def draw_wordmark(d: ImageDraw.ImageDraw, y: float = 210) -> None:
    """SignaLetter — semibold, muted-teal L (left-aligned like page 6)."""
    brand = font("SourceSerif4-Semibold.ttf", 92)
    left = 60
    # Draw in three pieces so L can be teal
    parts = [("Signa", PAPER), ("L", TEAL_LIGHT), ("etter", PAPER)]
    x = left
    for text, fill in parts:
        d.text((x, y), text, font=brand, fill=fill, anchor="lt")
        bbox = d.textbbox((x, y), text, font=brand)
        x = bbox[2]


def draw_card(
    path: Path,
    top_left: str,
    top_right: str,
    tagline: str,
) -> None:
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)

    mono = font("IBMPlexMono-Regular.ttf", 17)
    draw_tracked(d, (72, 56), top_left, mono, META, tracking=3.2)
    draw_tracked(d, (W - 72, 56), top_right, mono, META, tracking=3.2, anchor="rt")

    draw_wordmark(d, y=200)

    italic = font("SourceSerif4-It.ttf", 28)
    d.text((60, 330), tagline, font=italic, fill=PAPER, anchor="lt")

    draw_signal_mark(d, y=520)

    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG", optimize=True)
    assert path.stat().st_size < 300_000, path.stat().st_size
    print(f"{path.name}: {path.stat().st_size} bytes")


def main() -> None:
    # Sydney is on daylight time (AEDT) — prefer AEDT or SYDNEY, not AEST
    daily = "DAILY · 08:25 AEDT"
    cards = [
        (
            "default.png",
            daily,
            "MARKETS / AI",
            "Signal over noise. The few things that matter today.",
        ),
        (
            "markets.png",
            daily,
            "MARKETS",
            "ASX · Macro · Oil · Gold",
        ),
        (
            "ai.png",
            daily,
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
