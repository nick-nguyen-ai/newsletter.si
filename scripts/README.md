# Asset generation (Direction C)

Requires **Pillow** and **librsvg2-bin** (`rsvg-convert`).
OG generation uses TTFs under `scripts/fonts/` (Source Serif 4 + IBM Plex Mono).

```bash
pip install Pillow
python3 scripts/generate_brand.py   # favicon.ico, apple-touch, icon-192/512
python3 scripts/generate_og.py      # assets/og/*.png
```

# Markets v2 pipeline

```bash
pip install pyyaml jsonschema
python3 scripts/fetch_markets.py --issue-date 2026-10-19 --edition weekday --out snapshot.json
python3 scripts/build_markets_post.py --content markets-content.yml --snapshot snapshot.json --out _posts/2026-10-19-markets.md
python3 scripts/qa_markets.py --fix _posts/2026-10-19-markets.md
python3 scripts/tests/test_qa_markets.py
```
See docs/markets-post-format.md.
