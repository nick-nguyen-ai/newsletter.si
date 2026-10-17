# Logo options (pick one)

Three directions for Nick to choose before wiring into the site header/favicons.

| Option | Idea |
|--------|------|
| **A** | Classic editorial serif wordmark `newsletter.si` with refined `.si` accent |
| **B** | Modern minimal lowercase **n** monogram + wordmark |
| **C** | Data/signal mark (chart line as letterform) + wordmark |

Each folder has:

- `mark.svg` — icon / favicon source
- `lockup.svg` — horizontal wordmark (+ mark for B/C)
- `favicon-32.png` / `favicon-180.png` — raster previews

See **`compare.png`** for a side-by-side of lockups (light + dark) and favicon sizes.

Regenerate rasters:

```bash
python3 scripts/generate_brand_options.py
```

The live site header is **unchanged** until an option is selected.
