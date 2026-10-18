# SignaLetter — Direction C

Wordmark: **SignaLetter** (Source Serif 4). Primary = semibold with muted-teal **L**.
Domain stays `signaletter.si`.

| File | Use |
|------|-----|
| `mark-full.svg` | Full mark on paper |
| `mark-small.svg` | Small cut (no noise) |
| `mark-app-ink.svg` | App icon on ink |
| `mark-app-paper.svg` | App icon on paper |
| `mark-one-colour.svg` | Black + white stroke + teal dot |

Palette: Ink `#0F1724`, Paper `#F3F2EE`, muted teal `#2F7A75`, teal on dark `#66B8AC`, noise `#9A9A9A`.

Mark paths fitted to PDF crops (cubic beziers). PDF pages are raster-only.

```bash
python3 scripts/generate_brand.py
python3 scripts/generate_og.py
```
