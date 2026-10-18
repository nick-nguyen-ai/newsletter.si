#!/usr/bin/env python3
"""Generate SignaLetter Open Graph cards (1200×630) matching brand PDF page 6.

The share-card mark is rasterized from the same clean master SVG path used by
assets/brand/*.svg (uniform stroke, round caps) — not a polyline trace.
"""

from __future__ import annotations

import random
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "og"
FONTS = Path(__file__).resolve().parent / "fonts"
BRAND = ROOT / "assets" / "brand"

INK = (15, 23, 36)  # #0F1724
PAPER = (243, 242, 238)  # #F3F2EE
TEAL_LIGHT = (102, 184, 172)  # #66B8AC
META = (160, 168, 176)
NOISE_COL = (154, 154, 154)  # #9A9A9A

W, H = 1200, 630

# Master geometry (viewBox 0 0 549 548) — keep in sync with assets/brand/mark-*.svg
MASTER_PATH = (
    "M157 151 L157 402 "
    "C165 275 205 200 245 200 "
    "C285 192 304.0 342.0 355 385 "
    "C386.0 368.0 387.0 309.0 393 152 "
    "L393 400 L461 388"
)
MASTER_SW = 26.5
MASTER_TEAL = (490.77, 379.84)
MASTER_TEAL_R = 22.0
MASTER_VB_W, MASTER_VB_H = 549.0, 548.0
# Left-stem foot where the thin noise line joins the mark
MASTER_FOOT = (157.0, 402.0)


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


def noise_polyline(
    x0: float, x1: float, y: float, amp: float = 2.2, step: float = 7.0, seed: int = 11
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


def render_mark_rgba(scale: float) -> Image.Image:
    """Rasterize the master mark (no noise, no rounded rect) via rsvg for clean strokes."""
    sw = MASTER_SW
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{MASTER_VB_W}" height="{MASTER_VB_H}"
     viewBox="0 0 {MASTER_VB_W} {MASTER_VB_H}">
  <path d="{MASTER_PATH}" fill="none" stroke="#F3F2EE" stroke-width="{sw}"
        stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="{MASTER_TEAL[0]}" cy="{MASTER_TEAL[1]}" r="{MASTER_TEAL_R}" fill="#66B8AC"/>
</svg>'''
    out_w = max(1, int(round(MASTER_VB_W * scale)))
    out_h = max(1, int(round(MASTER_VB_H * scale)))
    with tempfile.TemporaryDirectory() as td:
        svg_path = Path(td) / "mark.svg"
        png_path = Path(td) / "mark.png"
        svg_path.write_text(svg)
        # Render at 2× then downscale for smoother edges
        subprocess.run(
            [
                "rsvg-convert",
                "-w",
                str(out_w * 2),
                "-h",
                str(out_h * 2),
                str(svg_path),
                "-o",
                str(png_path),
            ],
            check=True,
        )
        im = Image.open(png_path).convert("RGBA")
        return im.resize((out_w, out_h), Image.Resampling.LANCZOS)


def draw_signal_mark(card: Image.Image) -> None:
    """Thin grey noise along the bottom → clean SVG mark at bottom-right (~120px tall)."""
    d = ImageDraw.Draw(card)

    mark_h = 120.0
    scale = mark_h / (402 - 151)
    # Anchor by teal position measured from raw-001.jpg on 1200×630
    teal_target = (1111.0, 567.0)
    ox = teal_target[0] - MASTER_TEAL[0] * scale
    oy = teal_target[1] - MASTER_TEAL[1] * scale

    foot_x = ox + MASTER_FOOT[0] * scale
    foot_y = oy + MASTER_FOOT[1] * scale

    # Thin irregular noise (like raw-001) — not the icon's thick zigzag
    noise_pts = noise_polyline(72, foot_x, foot_y, amp=2.2, step=6.5, seed=11)
    d.line(noise_pts, fill=NOISE_COL, width=2, joint="curve")

    mark = render_mark_rgba(scale)
    # Paste with alpha onto ink card
    pos = (int(round(ox)), int(round(oy)))
    card.paste(mark, pos, mark)


def draw_card(path: Path, top_left: str, top_right: str, tagline: str) -> None:
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)

    mono = font("IBMPlexMono-Regular.ttf", 17)
    draw_tracked(d, (72, 56), top_left, mono, META, tracking=3.2)
    draw_tracked(d, (W - 72, 56), top_right, mono, META, tracking=3.2, anchor="rt")

    draw_wordmark(d, y=200)

    italic = font("SourceSerif4-It.ttf", 28)
    d.text((60, 330), tagline, font=italic, fill=PAPER, anchor="lt")

    draw_signal_mark(img)

    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG", optimize=True)
    assert path.stat().st_size < 300_000, path.stat().st_size
    print(f"{path.name}: {path.stat().st_size} bytes")


def main() -> None:
    daily = "DAILY · 08:25 AEDT"
    # Canonical filenames are *-v2.png (cache-bust for link previews).
    # Legacy names stay as identical copies so stale cached URLs still show new art.
    cards = [
        (
            "default-v2.png",
            daily,
            "MARKETS / AI",
            "Signal over noise. The few things that matter today.",
        ),
        (
            "markets-v2.png",
            daily,
            "MARKETS",
            "ASX · Macro · Oil · Gold",
        ),
        (
            "ai-v2.png",
            daily,
            "AI",
            "Coding agents · Evals · Models · Papers",
        ),
        (
            "archive-v2.png",
            "ARCHIVE",
            "MARKETS / AI",
            "Past issues. Still signal.",
        ),
    ]
    for name, left, right, tagline in cards:
        path = OUT / name
        draw_card(path, left, right, tagline)
        legacy = OUT / name.replace("-v2.png", ".png")
        legacy.write_bytes(path.read_bytes())
        print(f"{legacy.name}: copy of {name}")
    print("done", OUT)


if __name__ == "__main__":
    main()
