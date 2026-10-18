#!/usr/bin/env python3
"""Rasterize SignaLetter Direction C favicon / app icon set from SVG sources."""

from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / "assets" / "brand"
ICONS = ROOT / "assets" / "icons"


def rsvg(src: Path, dest: Path, size: int) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "rsvg-convert",
            "-w",
            str(size),
            "-h",
            str(size),
            str(src),
            "-o",
            str(dest),
        ],
        check=True,
    )


def main() -> None:
    ink = BRAND / "mark-app-ink.svg"
    small_src = ICONS / "favicon.svg"

    # App / PWA icons from ink app mark
    for name, size in [
        ("apple-touch-icon.png", 180),
        ("icon-192.png", 192),
        ("icon-512.png", 512),
        ("favicon-180.png", 180),
        ("favicon-32.png", 32),
    ]:
        rsvg(ink if size >= 48 else small_src, ICONS / name, size)

    # Multi-size ICO from small-cut favicon.svg
    frames = []
    for size in (16, 32, 48):
        tmp = ICONS / f"_tmp_{size}.png"
        rsvg(small_src, tmp, size)
        frames.append(Image.open(tmp).convert("RGBA"))
    frames[-1].save(
        ICONS / "favicon.ico",
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48)],
        append_images=frames[:-1],
    )
    for size in (16, 32, 48):
        (ICONS / f"_tmp_{size}.png").unlink(missing_ok=True)

    print("brand icons written to", ICONS)


if __name__ == "__main__":
    main()
