# SignaLetter — Direction C

Wordmark: **SignaLetter** (Source Serif 4). Primary = semibold with muted-teal **L**;
secondary = regular, ink only. Domain stays `signaletter.si`.

| File | Use |
|------|-----|
| `mark-full.svg` | Full mark (noise + nL signal + teal dot) on paper |
| `mark-small.svg` | Small cut (signal + teal, no noise) for tiny sizes |
| `mark-app-ink.svg` | App icon on ink (header light mode, PWA) |
| `mark-app-paper.svg` | App icon on paper (dark-mode header) |
| `mark-one-colour.svg` | One-colour cut (paper stroke on ink, teal dot) |

Palette: Ink `#0F1724`, Paper `#F3F2EE`, muted teal `#2F7A75`, teal on dark `#66B8AC`.

The mark paths were **redrawn** to match PDF pages 5–6 (PDF embeds rasters only — no extractable vectors).

```bash
python3 scripts/generate_brand.py
python3 scripts/generate_og.py
```
