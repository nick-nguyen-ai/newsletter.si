# Direction C — Signal over noise

Nick chose Claude Design’s **Direction C**.

| File | Use |
|------|-----|
| `mark-full.svg` | Full mark with noise squiggle + n-pulse + teal dot |
| `mark-small.svg` | Small cut (bold n + dot) for 16–48px |
| `mark-app-ink.svg` | App icon on ink (header, favicons, PWA) |
| `mark-app-paper.svg` | App icon on paper (dark-mode header) |
| `mark-one-colour.svg` | Single-colour (paper on ink) |

Palette: Ink `#0F1724`, Paper `#F3F2EE`, teal light `#2E7D72`, teal dark `#6BBFAE`.

Regenerate rasters:

```bash
python3 scripts/generate_brand.py
python3 scripts/generate_og.py
```
