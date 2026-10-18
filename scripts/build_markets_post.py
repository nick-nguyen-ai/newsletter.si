#!/usr/bin/env python3
"""Merge editorial content (YAML from the writer/reviewer) with the deterministic
market snapshot (JSON from fetch_markets.py) into a Markets v2 Jekyll post.

  python3 scripts/build_markets_post.py --content markets.yml --snapshot snapshot.json \
      --out _posts/2026-10-19-markets.md

The writer never types dashboard numbers: tiles come only from the snapshot.
Run scripts/qa_markets.py --fix on the output before publishing.
"""
import argparse
import json

import yaml

ORDER = ["title", "date", "section", "edition", "format", "cutoff_local", "session_note", "rerendered_from",
         "summary", "snapshot", "long_run_charts", "sections", "rates", "watchlist", "calendar", "dropped"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--content", required=True)
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    content = yaml.safe_load(open(a.content, encoding="utf-8"))
    snap = json.load(open(a.snapshot, encoding="utf-8"))
    fm = dict(content)
    fm["section"] = "markets"
    fm["format"] = "markets-v2"
    fm.setdefault("edition", snap["edition"])
    fm["cutoff_local"] = snap["cutoff_local"]
    fm["snapshot"] = {k: snap[k] for k in ("generated_by", "retrieved_at_utc", "cutoff_utc", "backfill") if k in snap}
    fm["snapshot"]["quotes"] = snap["quotes"]
    fm["dropped"] = list(snap.get("dropped", [])) + list(content.get("dropped", []) or [])
    ordered = {k: fm[k] for k in ORDER if k in fm}
    ordered.update({k: v for k, v in fm.items() if k not in ordered})
    date = ordered.pop("date")
    text = "---\n" + yaml.safe_dump(ordered, sort_keys=False, allow_unicode=True, width=1000)
    # keep the original date literal (it drives the permalink)
    text = text.replace("title:", f"title:", 1)
    head, rest = text.split("\n", 2)[0:2], text.split("\n", 2)[2]
    text = head[0] + "\n" + head[1] + f"\ndate: {date}\n" + rest
    text += "---\n<!-- Markets v2: rendered from front matter by _includes/markets-report.html -->\n"
    open(a.out, "w", encoding="utf-8").write(text)


if __name__ == "__main__":
    main()
