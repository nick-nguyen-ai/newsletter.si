# Asset generation (Direction C)

Requires **Pillow** and **librsvg2-bin** (`rsvg-convert`).
OG generation uses TTFs under `scripts/fonts/` (Source Serif 4 + IBM Plex Mono).

```bash
pip install Pillow
python3 scripts/generate_brand.py   # favicon.ico, apple-touch, icon-192/512
python3 scripts/generate_og.py      # assets/og/*.png
```
