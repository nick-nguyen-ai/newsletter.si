#!/usr/bin/env python3
"""Build assets/data/asx-tickers.json: the tickers readers may add to "My shares".

Allowed list = S&P/ASX 300 constituents, taken from the holdings of the Vanguard
Australian Shares Index ETF (VAS), which fully replicates the S&P/ASX 300 (Vanguard's
public holdings API, updated monthly; ~300 index stocks plus a few holdings pending
corporate actions). Only codes still on ASX's official listed-companies file are
kept, plus the site's default watchlist (_data/watchlist.csv). Names come from ASX's
official file. Refresh after each S&P rebalance (March/September) and monthly is fine.

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
VAS = "https://www.vanguard.com.au/personal/api/data/products/holdings/8205?limit=400"
VAS_PAGE = "https://www.vanguard.com.au/personal/invest-with-us/etf?portId=8205&tab=holdings"
ASX_CSV = "https://www.asx.com.au/asx/research/ASXListedCompanies.csv"
UA = {"User-Agent": "Mozilla/5.0 (SignaLetter/0.1; +https://signaletter.si)", "Accept": "application/json, text/csv, */*",
      "Referer": VAS_PAGE}


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
    items = json.loads(get(VAS))["data"]["items"]
    eff = sorted({i.get("effectiveDate") for i in items if i.get("effectiveDate")})
    lines = get(ASX_CSV).splitlines()
    as_at = lines[0].strip()
    listed = {r[1]: r[0] for r in csv.reader(lines[2:]) if len(r) > 1}
    by_name = {re.sub(r"[^A-Z]", "", v.upper().replace("LIMITED", "LTD")): k for k, v in listed.items()}
    codes, unmatched = [], []
    for i in items:
        c = (i.get("ticker") or "").strip().upper()
        if not re.fullmatch(r"[A-Z0-9]{3}", c):  # missing/odd ticker (e.g. pending corporate action): match by name
            c = by_name.get(re.sub(r"[^A-Z]", "", (i.get("name") or "").upper().replace("LIMITED", "LTD")), "")
            if not c:
                unmatched.append(i.get("name")); continue
        if c not in codes:
            codes.append(c)
    defaults = [r["ticker"] for r in csv.DictReader(open(ROOT / "_data" / "watchlist.csv"))]
    keep = sorted({c for c in codes if c in listed} | {c for c in defaults if c in listed})
    dropped = [c for c in codes if c not in listed]
    out = {
        "generated_by": "scripts/build_asx_list.py",
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "max_per_reader": 10,
        "sources": [
            {"label": "S&P/ASX 300 constituents via Vanguard VAS holdings as at %s (VAS fully replicates the S&P/ASX 300)"
             % ",".join(eff), "url": VAS_PAGE},
            {"label": as_at, "url": ASX_CSV},
        ],
        "universe": "S&P/ASX 300",
        "dropped_not_listed": dropped,
        "unmatched_holdings": unmatched,
        "default_watchlist": defaults,
        "tickers": [{"code": c, "name": pretty(listed[c]), "official_name": listed[c]} for c in keep],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {OUT} with {len(keep)} tickers; dropped {dropped}; unmatched {unmatched}")


if __name__ == "__main__":
    main()
