#!/usr/bin/env python3
"""Merge editorial content (YAML from the writer/reviewer) with the deterministic
market snapshot (JSON from fetch_markets.py) into a Markets v2 Jekyll post.

  python3 scripts/build_markets_post.py --content markets.yml --snapshot snapshot.json \
      --out _posts/2026-10-19-markets.md

  # Merge an after-the-close edition into an existing post:
  python3 scripts/build_markets_post.py --close close-content.yml \
      --snapshot assets/issues/2026-10-19/close-snapshot.json \
      --out _posts/2026-10-19-markets.md

The writer never types dashboard numbers: tiles come only from the snapshot.
Run scripts/qa_markets.py --fix on the output before publishing.

Title format: "Markets: Monday 19 October" (weekday name + day + month).
Weekend vs weekday is shown via the edition badge, not the title.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys

import yaml

ORDER = [
    "title", "date", "section", "edition", "format", "cutoff_local", "session_note",
    "rerendered_from", "summary", "snapshot", "long_run_charts", "sections", "rates",
    "watchlist", "calendar", "close", "dropped",
]

CLOSE_ORDER = [
    "preview", "cutoff_local", "session_note", "summary", "snapshot", "long_run_charts",
    "sections", "rates", "watchlist", "calendar", "dropped",
]


def markets_title(date_val) -> str:
    """Markets: Monday 19 October"""
    if isinstance(date_val, dt.datetime):
        d = date_val.date()
    elif isinstance(date_val, dt.date):
        d = date_val
    else:
        d = dt.date.fromisoformat(str(date_val)[:10])
    # %-d is Linux/glibc; fall back for portability
    try:
        day = d.strftime("%-d")
    except ValueError:
        day = str(d.day)
    return f"Markets: {d.strftime('%A')} {day} {d.strftime('%B')}"


def split_front_matter(text: str):
    if not text.startswith("---"):
        raise ValueError("no front matter")
    _, fm, body = text.split("---", 2)
    return yaml.safe_load(fm), body


def dump_post(fm: dict, body: str) -> str:
    date = fm.get("date")
    ordered = {k: fm[k] for k in ORDER if k in fm}
    ordered.update({k: v for k, v in fm.items() if k not in ordered})
    date_val = ordered.pop("date", date)
    text = "---\n" + yaml.safe_dump(ordered, sort_keys=False, allow_unicode=True, width=1000)
    # Keep the original date literal (it drives the permalink)
    head, rest = text.split("\n", 2)[0:2], text.split("\n", 2)[2]
    text = head[0] + "\n" + head[1] + f"\ndate: {date_val}\n" + rest
    if not body.strip():
        body = "\n<!-- Markets v2: rendered from front matter by _includes/markets-report.html -->\n"
    elif not body.startswith("\n"):
        body = "\n" + body
    return text + "---" + body


def build_morning(content_path: str, snapshot_path: str, out_path: str) -> None:
    content = yaml.safe_load(open(content_path, encoding="utf-8"))
    snap = json.load(open(snapshot_path, encoding="utf-8"))
    fm = dict(content)
    fm["section"] = "markets"
    fm["format"] = "markets-v2"
    fm.setdefault("edition", snap["edition"])
    fm["cutoff_local"] = snap["cutoff_local"]
    fm["snapshot"] = {k: snap[k] for k in ("generated_by", "retrieved_at_utc", "cutoff_utc", "backfill", "mode") if k in snap}
    fm["snapshot"]["quotes"] = snap["quotes"]
    fm["dropped"] = list(snap.get("dropped", [])) + list(content.get("dropped", []) or [])
    if "title" not in fm or not str(fm.get("title", "")).startswith("Markets:"):
        fm["title"] = markets_title(fm.get("date") or snap.get("issue_date"))
    open(out_path, "w", encoding="utf-8").write(dump_post(fm, ""))


def build_close(close_path: str, snapshot_path: str, out_path: str) -> None:
    """Merge close editorial YAML + close snapshot into an existing Markets post."""
    text = open(out_path, encoding="utf-8").read()
    fm, body = split_front_matter(text)
    close_content = yaml.safe_load(open(close_path, encoding="utf-8")) or {}
    snap = json.load(open(snapshot_path, encoding="utf-8"))
    close = dict(close_content)
    close["cutoff_local"] = snap["cutoff_local"]
    close["snapshot"] = {
        k: snap[k] for k in ("generated_by", "retrieved_at_utc", "cutoff_utc", "backfill", "mode") if k in snap
    }
    close["snapshot"]["quotes"] = snap["quotes"]
    close["dropped"] = list(snap.get("dropped", [])) + list(close_content.get("dropped", []) or [])
    # Preserve key order for readability
    ordered_close = {k: close[k] for k in CLOSE_ORDER if k in close}
    ordered_close.update({k: v for k, v in close.items() if k not in ordered_close})
    fm["close"] = ordered_close
    # Ensure title format on merge too
    if not str(fm.get("title", "")).startswith("Markets:"):
        fm["title"] = markets_title(fm.get("date") or snap.get("issue_date"))
    open(out_path, "w", encoding="utf-8").write(dump_post(fm, body))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--content", help="morning editorial YAML")
    ap.add_argument("--close", dest="close_content", help="close editorial YAML to merge into --out")
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.close_content:
        if a.content:
            print("error: use either --content or --close, not both", file=sys.stderr)
            sys.exit(2)
        build_close(a.close_content, a.snapshot, a.out)
    elif a.content:
        build_morning(a.content, a.snapshot, a.out)
    else:
        print("error: --content or --close is required", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
