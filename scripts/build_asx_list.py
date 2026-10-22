#!/usr/bin/env python3
"""Build assets/data/asx-tickers.json: the tickers readers may add to "My shares".

Allowed list = S&P/ASX 200 constituents (Wikipedia table snapshot, community
maintained, so approximate) that are still on ASX's official listed-companies
file, plus the site's default watchlist (_data/watchlist.csv). Names come from
ASX's official file. Refresh after each quarterly S&P rebalance; replace the
Wikipedia source with an official constituent file when one is licensed.

Usage: python3 scripts/build_asx_list.py
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "data" / "asx-tickers.json"
WIKI = "https://en.wikipedia.org/w/api.php?action=parse&page=S%26P/ASX_200&prop=wikitext|revid&format=json"
ASX_CSV = "https://www.asx.com.au/asx/research/ASXListedCompanies.csv"
UA = {"User-Agent": "SignaLetter/0.1 (+https://signaletter.si)"}


def get(url: str) -> str:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return r.read().decode("utf-8", "replace")


SMALL = {"OF", "AND", "THE", "&", "FOR"}
SUFFIX = re.compile(r"\s+(LIMITED|LTD|GROUP LIMITED|CORPORATION LIMITED|HOLDINGS LIMITED)$")


def pretty(name: str) -> str:
    """'COMMONWEALTH BANK OF AUSTRALIA.' -> 'Commonwealth Bank of Australia'; short codes stay upper."""
    n = name.strip().rstrip(".")
    n = re.sub(r"\s+(LIMITED|LTD)$", "", n)
    out = []
    for i, w in enumerate(n.split()):
        if w in SMALL and i:
            out.append(w.lower())
        elif len(w) <= 3 and w.isalpha() and w not in {"CO", "INC"}:
            out.append(w)
        else:
            out.append(w.capitalize())
    return " ".join(out)


def main() -> None:
    wj = json.loads(get(WIKI))["parse"]
    codes = []
    for row in wj["wikitext"]["*"].split("|-"):
        m = re.match(r"\s*\|\s*([A-Z0-9]{3})\s*(\||\n)", row)
        if m and m.group(1) not in codes:
            codes.append(m.group(1))
    lines = get(ASX_CSV).splitlines()
    as_at = lines[0].strip()
    listed = {r[1]: r[0] for r in csv.reader(lines[2:]) if len(r) > 1}
    defaults = [r["ticker"] for r in csv.DictReader(open(ROOT / "_data" / "watchlist.csv"))]
    keep = sorted({c for c in codes if c in listed} | {c for c in defaults if c in listed})
    dropped = [c for c in codes if c not in listed]
    out = {
        "generated_by": "scripts/build_asx_list.py",
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "max_per_reader": 10,
        "sources": [
            {"label": "Wikipedia: S&P/ASX 200 constituents (revision %s, approximate)" % wj.get("revid"),
             "url": "https://en.wikipedia.org/wiki/S%26P/ASX_200"},
            {"label": as_at, "url": ASX_CSV},
        ],
        "dropped_not_listed": dropped,
        "default_watchlist": defaults,
        "tickers": [{"code": c, "name": pretty(listed[c]), "official_name": listed[c]} for c in keep],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {OUT} with {len(keep)} tickers; dropped {dropped}")


if __name__ == "__main__":
    main()
