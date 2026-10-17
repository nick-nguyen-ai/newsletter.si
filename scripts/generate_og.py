#!/usr/bin/env python3
"""Generate branded 1200×630 Open Graph PNGs (neutral serif wordmark, no logo mark)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "og"

SERIF_B = "/usr/share/fonts/truetype/noto/NotoSerif-Bold.ttf"
SERIF_R = "/usr/share/fonts/truetype/noto/NotoSerif-Regular.ttf"
SANS = "/usr/share/fonts/truetype/lato/Lato-Regular.ttf"
SANS_B = "/usr/share/fonts/truetype/lato/Lato-Bold.ttf"

W, H = 1200, 630


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def gradient_bg(left=(8, 18, 32), right=(18, 55, 68)) -> Image.Image:
    img = Image.new("RGB", (W, H))
    px = img.load()
    for x in range(W):
        t = x / (W - 1)
        # slight vertical vignette
        for y in range(H):
            v = y / (H - 1)
            r = int(lerp(left[0], right[0], t) * (1 - 0.08 * v))
            g = int(lerp(left[1], right[1], t) * (1 - 0.06 * v))
            b = int(lerp(left[2], right[2], t) * (1 - 0.05 * v))
            px[x, y] = (r, g, b)
    return img


def draw_card(path: Path, topic: str, tagline: str, accent=(13, 110, 110)) -> None:
    img = gradient_bg()
    d = ImageDraw.Draw(img)

    # left accent rule
    d.rectangle([0, 0, 10, H], fill=accent)

    # brand wordmark (neutral serif — no monogram)
    brand = font(SERIF_B, 64)
    d.text((72, 150), "newsletter", font=brand, fill=(245, 242, 234), anchor="lm")
    bbox = d.textbbox((72, 150), "newsletter", font=brand, anchor="lm")
    d.text((bbox[2] + 4, 150), ".si", font=brand, fill=accent, anchor="lm")

    # topic
    d.text((72, 280), topic, font=font(SERIF_R, 42), fill=(168, 198, 210), anchor="lm")

    # tagline
    d.text((72, 360), tagline, font=font(SANS, 26), fill=(196, 165, 116), anchor="lm")

    # footer domain
    d.text((72, 560), "nick-nguyen-ai.github.io/newsletter.si", font=font(SANS, 20), fill=(120, 140, 150), anchor="lm")

    # subtle top hairline
    d.line([(72, 100), (520, 100)], fill=(40, 70, 85), width=1)

    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG", optimize=True)
    assert path.stat().st_size < 300_000, path.stat().st_size
    print(f"{path.name}: {path.stat().st_size} bytes")


def main() -> None:
    cards = [
        ("default.png", "Daily briefing", "ASX markets · global macro · AI"),
        ("markets.png", "Markets", "ASX morning briefings & weekend macro"),
        ("ai.png", "AI", "Coding agents · evals · research"),
        ("archive.png", "Archive", "Past markets & AI issues"),
    ]
    for name, topic, tagline in cards:
        draw_card(OUT / name, topic, tagline)
    print("done", OUT)


if __name__ == "__main__":
    main()
