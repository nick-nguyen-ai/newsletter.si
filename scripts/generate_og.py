#!/usr/bin/env python3
"""Generate SignaLetter Open Graph cards (1200×630) matching brand PDF page 6."""

from __future__ import annotations

import math
import random
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "og"
FONTS = Path(__file__).resolve().parent / "fonts"
BRAND = ROOT / "assets" / "brand"

INK = (15, 23, 36)  # #0F1724
PAPER = (243, 242, 238)  # #F3F2EE
TEAL_LIGHT = (102, 184, 172)  # #66B8AC — on dark
META = (160, 168, 176)
NOISE_COL = (154, 154, 154)  # #9A9A9A

W, H = 1200, 630

# Master path fitted to mark-paper.png (viewBox 0..549 × 0..548)
MASTER_PATH = (
    "M157 151 L157 402 "
    "C169.0 268.0 194.0 219.0 245 200 "
    "C325.0 241.0 294.0 352.0 355 385 "
    "C386.0 368.0 387.0 309.0 393 152 "
    "L393 400 L461 388"
)
MASTER_SW = 26.5
MASTER_TEAL = (490.77, 379.84)
MASTER_TEAL_R = 22.0
MASTER_VB = (549.0, 548.0)


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = FONTS / name
    if not path.exists():
        alts = {
            "SourceSerif4-Semibold.ttf": "/tmp/SourceSerif4-Semibold.ttf",
            "SourceSerif4-It.ttf": "/tmp/SourceSerif4-It.ttf",
            "IBMPlexMono-Regular.ttf": "/usr/share/fonts/truetype/ibm-plex/IBMPlexMono-Regular.ttf",
        }
        path = Path(alts.get(name, str(path)))
    return ImageFont.truetype(str(path), size)


def parse_path(d: str) -> list[tuple[str, list[float]]]:
    """Parse a simple SVG path of M/L/C commands into segments."""
    tokens = re.findall(r"[MLC]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", d)
    segs: list[tuple[str, list[float]]] = []
    i = 0
    while i < len(tokens):
        cmd = tokens[i]
        i += 1
        nums: list[float] = []
        while i < len(tokens) and tokens[i] not in "MLC":
            nums.append(float(tokens[i]))
            i += 1
        segs.append((cmd, nums))
    return segs


def sample_path(d: str, n_per_cubic: int = 32) -> list[tuple[float, float]]:
    segs = parse_path(d)
    pts: list[tuple[float, float]] = []
    cx = cy = 0.0
    for cmd, nums in segs:
        if cmd == "M":
            cx, cy = nums[0], nums[1]
            pts.append((cx, cy))
        elif cmd == "L":
            cx, cy = nums[0], nums[1]
            pts.append((cx, cy))
        elif cmd == "C":
            x1, y1, x2, y2, x3, y3 = nums
            x0, y0 = cx, cy
            for i in range(1, n_per_cubic + 1):
                t = i / n_per_cubic
                u = 1 - t
                x = u**3 * x0 + 3 * u**2 * t * x1 + 3 * u * t**2 * x2 + t**3 * x3
                y = u**3 * y0 + 3 * u**2 * t * y1 + 3 * u * t**2 * y2 + t**3 * y3
                pts.append((x, y))
            cx, cy = x3, y3
    return pts


def noise_polyline(
    x0: float, x1: float, y: float, amp: float = 2.6, step: float = 7.0, seed: int = 11
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


def draw_tracked(
    d: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    font_obj,
    fill,
    tracking: float = 3.5,
    anchor: str = "lt",
) -> None:
    x, y = xy
    widths = []
    for ch in text:
        bbox = d.textbbox((0, 0), ch, font=font_obj)
        widths.append(bbox[2] - bbox[0])
    total = sum(widths) + tracking * max(0, len(text) - 1)
    if anchor == "rt":
        x = x - total
    for ch, w in zip(text, widths):
        d.text((x, y), ch, font=font_obj, fill=fill)
        x += w + tracking


def draw_wordmark(d: ImageDraw.ImageDraw, y: float = 200) -> None:
    brand = font("SourceSerif4-Semibold.ttf", 92)
    left = 60
    parts = [("Signa", PAPER), ("L", TEAL_LIGHT), ("etter", PAPER)]
    x = left
    for text, fill in parts:
        d.text((x, y), text, font=brand, fill=fill, anchor="lt")
        bbox = d.textbbox((x, y), text, font=brand)
        x = bbox[2]


def draw_signal_mark(d: ImageDraw.ImageDraw) -> None:
    """Long grey noise along the bottom → master nL mark at bottom-right (~120px tall).

    Placement tuned to raw-001.jpg share card: teal ≈ (1111, 567) on 1200×630.
    """
    # ~120px tall on 1200×630 (master left-stem span 151→402)
    mark_h = 120.0
    scale = mark_h / (402 - 151)
    # Anchor by teal position from raw-001 (scaled to 1200×630)
    teal_target = (1111.0, 567.0)
    ox = teal_target[0] - MASTER_TEAL[0] * scale
    oy = teal_target[1] - MASTER_TEAL[1] * scale

    def X(u: float) -> float:
        return ox + u * scale

    def Y(v: float) -> float:
        return oy + v * scale

    # Noise from left margin into left-stem foot (no stray diagonals)
    foot_x, foot_y = X(157), Y(402)
    noise_pts = noise_polyline(72, foot_x, foot_y, amp=2.4, step=6.5, seed=11)
    d.line(noise_pts, fill=NOISE_COL, width=2, joint="curve")

    pts = [(X(x), Y(y)) for x, y in sample_path(MASTER_PATH)]
    sw = max(3, int(round(MASTER_SW * scale)))
    d.line(pts, fill=PAPER, width=sw, joint="curve")
    r = sw / 2
    for p in (pts[0], pts[-1]):
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=PAPER)

    tx, ty = X(MASTER_TEAL[0]), Y(MASTER_TEAL[1])
    tr = MASTER_TEAL_R * scale
    d.ellipse([tx - tr, ty - tr, tx + tr, ty + tr], fill=TEAL_LIGHT)


def draw_card(path: Path, top_left: str, top_right: str, tagline: str) -> None:
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)

    mono = font("IBMPlexMono-Regular.ttf", 17)
    draw_tracked(d, (72, 56), top_left, mono, META, tracking=3.2)
    draw_tracked(d, (W - 72, 56), top_right, mono, META, tracking=3.2, anchor="rt")

    draw_wordmark(d, y=200)

    italic = font("SourceSerif4-It.ttf", 28)
    d.text((60, 330), tagline, font=italic, fill=PAPER, anchor="lt")

    draw_signal_mark(d)

    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG", optimize=True)
    assert path.stat().st_size < 300_000, path.stat().st_size
    print(f"{path.name}: {path.stat().st_size} bytes")


def main() -> None:
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
