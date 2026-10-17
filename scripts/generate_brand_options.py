#!/usr/bin/env python3
"""Rasterize brand option SVGs and build assets/brand/options/compare.png."""

from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OPTS = ROOT / "assets" / "brand" / "options"
SERIF = "/usr/share/fonts/truetype/noto/NotoSerif-Bold.ttf"
SERIF_R = "/usr/share/fonts/truetype/noto/NotoSerif-Regular.ttf"
SANS = "/usr/share/fonts/truetype/lato/Lato-Regular.ttf"
SANS_B = "/usr/share/fonts/truetype/lato/Lato-Bold.ttf"

INK = (11, 28, 44)
CREAM = (245, 242, 234)
MUTED = (120, 130, 140)
TEAL = (13, 110, 110)


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def rasterize(svg: Path, out: Path, size: int) -> None:
    subprocess.run(
        [
            "rsvg-convert",
            "-w",
            str(size),
            "-h",
            str(size),
            "-o",
            str(out),
            str(svg),
        ],
        check=True,
    )


def lockup_on(bg: tuple[int, int, int], lockup_svg: Path, width: int = 520) -> Image.Image:
    """Render lockup SVG onto a solid background panel."""
    tmp = lockup_svg.with_suffix(".tmp.png")
    # Rasterize lockup at 2x then composite
    subprocess.run(
        ["rsvg-convert", "-w", str(width), "-o", str(tmp), str(lockup_svg)],
        check=True,
    )
    mark = Image.open(tmp).convert("RGBA")
    tmp.unlink(missing_ok=True)

    # Dark lockups use dark fills — for dark bg, recolor ink fills to cream via a light panel version
    panel_h = 120
    panel = Image.new("RGB", (width + 48, panel_h), bg)
    # If background is dark, the lockup SVG is dark-on-transparent text — need a light variant.
    # For dark panels we invert by drawing white wordmark with Pillow for options A–C labels
    # instead: composite the SVG only on light; on dark redraw wordmark.
    if bg[0] < 40:
        # dark panel: rebuild a light wordmark from the option letter in the folder name
        return dark_lockup_panel(lockup_svg.parent.name, width + 48, panel_h)
    panel.paste(mark, (24, (panel_h - mark.height) // 2), mark)
    return panel


def dark_lockup_panel(opt: str, w: int, h: int) -> Image.Image:
    img = Image.new("RGB", (w, h), INK)
    d = ImageDraw.Draw(img)
    f = font(SERIF, 34)
    if opt == "a":
        # newsletter + .si accent
        d.text((24, 38), "newsletter", font=f, fill=CREAM, anchor="lm")
        bbox = d.textbbox((24, 38), "newsletter", font=f, anchor="lm")
        d.text((bbox[2] + 2, 38), ".si", font=f, fill=TEAL, anchor="lm")
    elif opt == "b":
        # small mark + wordmark
        d.rounded_rectangle((24, 32, 72, 80), radius=10, fill=(20, 40, 55))
        d.text((36, 56), "n", font=font(SERIF, 28), fill=CREAM, anchor="mm")
        d.text((84, 56), "newsletter.si", font=f, fill=CREAM, anchor="lm")
    else:
        d.rounded_rectangle((24, 32, 72, 80), radius=9, fill=(20, 40, 55))
        # mini signal
        d.line([(34, 70), (34, 48), (48, 42), (48, 70)], fill=CREAM, width=3, joint="curve")
        d.line([(48, 50), (62, 40)], fill=TEAL, width=3)
        d.ellipse([(59, 37), (65, 43)], fill=(196, 165, 116))
        d.text((84, 56), "newsletter.si", font=f, fill=CREAM, anchor="lm")
    return img


def build_compare() -> Path:
    labels = {
        "a": "A · Classic editorial",
        "b": "B · Modern monogram",
        "c": "C · Signal mark",
    }
    col_w = 640
    row_h = 420
    header = 72
    img = Image.new("RGB", (col_w * 3 + 48, header + row_h + 24), (250, 249, 247))
    d = ImageDraw.Draw(img)
    d.text(
        (24, 36),
        "newsletter.si — logo options (not yet applied)",
        font=font(SERIF, 26),
        fill=INK,
        anchor="lm",
    )

    for i, key in enumerate(("a", "b", "c")):
        x0 = 24 + i * col_w
        y0 = header
        folder = OPTS / key
        # column label
        d.text((x0, y0 + 8), labels[key], font=font(SANS_B, 16), fill=TEAL)

        light = lockup_on(CREAM, folder / "lockup.svg", width=520)
        dark = dark_lockup_panel(key, light.width, light.height)
        img.paste(light, (x0, y0 + 36))
        img.paste(dark, (x0, y0 + 36 + light.height + 12))

        fav32 = Image.open(folder / "favicon-32.png").convert("RGBA")
        fav180 = Image.open(folder / "favicon-180.png").convert("RGBA")
        fy = y0 + 36 + light.height + 12 + dark.height + 16
        d.text((x0, fy), "favicon 32", font=font(SANS, 12), fill=MUTED)
        d.text((x0 + 100, fy), "favicon 180", font=font(SANS, 12), fill=MUTED)
        # checkerboards behind favicons
        def checker(box, cell=8):
            x1, y1, x2, y2 = box
            for yy in range(y1, y2, cell):
                for xx in range(x1, x2, cell):
                    c = (230, 230, 228) if ((xx // cell) + (yy // cell)) % 2 == 0 else (255, 255, 255)
                    d.rectangle([xx, yy, min(xx + cell, x2), min(yy + cell, y2)], fill=c)

        checker((x0, fy + 18, x0 + 40, fy + 58))
        img.paste(fav32, (x0 + 4, fy + 22), fav32)
        checker((x0 + 100, fy + 18, x0 + 100 + 100, fy + 18 + 100))
        fav180_sm = fav180.resize((96, 96), Image.Resampling.LANCZOS)
        img.paste(fav180_sm, (x0 + 102, fy + 20), fav180_sm)

    out = OPTS / "compare.png"
    img.save(out, "PNG", optimize=True)
    return out


def main() -> None:
    for key in ("a", "b", "c"):
        folder = OPTS / key
        mark = folder / "mark.svg"
        rasterize(mark, folder / "favicon-32.png", 32)
        rasterize(mark, folder / "favicon-180.png", 180)
        print("rasters", key, "ok")
    out = build_compare()
    print("wrote", out, "bytes", out.stat().st_size)


if __name__ == "__main__":
    main()
