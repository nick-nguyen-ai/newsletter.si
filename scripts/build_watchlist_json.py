#!/usr/bin/env python3
"""Build assets/issues/YYYY-MM-DD/watchlist.json for the per-reader "My shares" view.

One entry per ticker that any reader follows, for each edition the day's Markets
post has (morning; close when the post has a close block). Facts only:

* Price and change: if the post's own snapshot has a wl_<ticker> quote, that exact
  quote is reused (so the default watchlist matches the page). Otherwise the
  Yahoo Finance chart API daily close (delayed, unofficial), compared with the
  previous session's close. Morning = previous ASX session; close = the post date.
* Note: if the post's reviewed watchlist block has the ticker, its note,
  next_catalyst and sources are reused verbatim. Otherwise the note lists ASX
  announcement headlines (ASX/Markit announcements feed) released in the edition
  window, or says there were none. If a source fails, the entry says the data
  is not available rather than guessing.

Usage:
  python3 scripts/build_watchlist_json.py --date 2026-10-22 --tickers ZIP,CSL,BHP,CBA
  python3 scripts/build_watchlist_json.py --date 2026-10-22 --tickers-file subscribers_tickers.txt
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

ROOT = Path(__file__).resolve().parents[1]
SYD = ZoneInfo("Australia/Sydney")
UA = {"User-Agent": "Mozilla/5.0 (SignaLetter watchlist builder)"}
YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}.AX?range=1mo&interval=1d"
ANN = "https://asx.api.markitdigital.com/asx-research/1.0/companies/{t}/announcements"
ASX_PAGE = "https://www.asx.com.au/markets/trade-our-cash-market/announcements.{t}"
YAHOO_LICENCE = "Yahoo Finance chart data: delayed, unofficial; Yahoo terms restrict redistribution. Shown as a cited single quote only."


def get_json(url: str):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def signed(v: float, decimals: int) -> str:
    s = f"{abs(v):,.{decimals}f}"
    return ("+" if v > 0 else "−" if v < 0 else "±") + s


def load_post(day: str) -> dict:
    p = ROOT / "_posts" / f"{day}-markets.md"
    text = p.read_text()
    return yaml.safe_load(text.split("---", 2)[1])


def yahoo_closes(t: str) -> dict[str, float]:
    d = get_json(YAHOO.format(sym=t))["chart"]["result"][0]
    out: dict[str, float] = {}
    for ts, c in zip(d.get("timestamp") or [], d["indicators"]["quote"][0].get("close") or []):
        if c is None:
            continue
        out[dt.datetime.fromtimestamp(ts, SYD).date().isoformat()] = c  # last value per date wins
    return out


def announcements(t: str) -> list[dict]:
    return get_json(ANN.format(t=t))["data"].get("items") or []


def price_block(t: str, closes: dict[str, float] | None, session: str, quote: dict | None) -> dict:
    if quote and quote.get("status") == "ok" and quote.get("market_session_date") == session:
        return {
            "status": "ok", "session_date": session, "value": quote["value"],
            "display_value": quote["display_value"], "change_pct": quote.get("change_pct"),
            "display_change": quote["display_change"], "provider": quote["provider"],
            "provider_url": quote["provider_url"], "licence_note": quote.get("licence_note"),
            "from": "post snapshot",
        }
    if not closes or session not in closes:
        return {"status": "unavailable", "session_date": session}
    prev = [d for d in sorted(closes) if d < session]
    if not prev:
        return {"status": "unavailable", "session_date": session}
    v, pv = closes[session], closes[prev[-1]]
    pct = (v / pv - 1) * 100
    dec = 3 if v < 1 else 2
    return {
        "status": "ok", "session_date": session, "value": round(v, 4),
        "display_value": f"{v:,.{dec}f}", "comparison_date": prev[-1], "comparison_value": round(pv, 4),
        "change_pct": round(pct, 2), "display_change": signed(round(pct, 1), 1) + "%",
        "provider": f"Yahoo Finance ({t}.AX)", "provider_url": f"https://finance.yahoo.com/quote/{t}.AX/",
        "licence_note": YAHOO_LICENCE, "from": "yahoo chart api",
    }


def note_from_announcements(t: str, anns: list[dict] | None, start: dt.datetime, end: dt.datetime,
                            px: dict, session_word: str) -> dict:
    move = ""
    if px["status"] == "ok":
        shown = px["display_change"].rstrip("%")  # e.g. "+0.4", "−2.4", "±0.0": reuse the displayed figure
        sign, mag = shown[0], shown[1:]
        if float(mag) == 0:
            move = f"Little changed at A${px['display_value']} {session_word}."
        else:
            verb = "Rose" if sign == "+" else "Fell"
            move = f"{verb} {mag}% to A${px['display_value']} {session_word}."
    if anns is None:
        return {"note": (move + " ASX announcements not in our data.").strip(), "sources": []}
    # The feed returns only the latest 5 items; if even the oldest is inside or after the
    # window, earlier ones in the window may be missing, so say so instead of "none".
    dates = [dt.datetime.fromisoformat(a["date"].replace("Z", "+00:00")).astimezone(SYD) for a in anns]
    truncated = len(anns) >= 5 and min(dates) > start
    hits = []
    for a in anns:
        when = dt.datetime.fromisoformat(a["date"].replace("Z", "+00:00")).astimezone(SYD)
        if start <= when <= end:
            hits.append((when, a))
    if not hits and truncated:
        return {"note": (move + " ASX announcements for this window not fully in our data.").strip(),
                "sources": [{"label": f"ASX announcements ({t})", "url": ASX_PAGE.format(t=t.lower()),
                             "claim_type": "official_statement"}]}
    if not hits:
        return {"note": (move + " No new ASX announcement.").strip(),
                "sources": [{"label": f"ASX announcements ({t})", "url": ASX_PAGE.format(t=t.lower()),
                             "claim_type": "official_statement"}]}
    parts = []
    for when, a in sorted(hits, key=lambda x: x[0])[:3]:
        ps = " (price sensitive)" if a.get("isPriceSensitive") else ""
        parts.append(f"“{a['headline'].strip()}”{ps}, {when.strftime('%-d %b %-I:%M%p').replace('AM', 'am').replace('PM', 'pm')} {when.strftime('%Z')}")
    more = f" and {len(hits) - 3} more" if len(hits) > 3 else ""
    word = "announcement" if len(hits) == 1 else "announcements"
    lead = f" ASX {word} include: " if truncated else f" ASX {word}: "
    note = (move + lead + "; ".join(parts) + more + ".").strip()
    return {"note": note, "sources": [{"label": f"ASX announcements ({t})", "url": ASX_PAGE.format(t=t.lower()),
                                       "claim_type": "official_statement"}]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--tickers", default="")
    ap.add_argument("--tickers-file")
    args = ap.parse_args()
    tickers = [x.strip().upper() for x in args.tickers.split(",") if x.strip()]
    if args.tickers_file:
        tickers += [x.strip().upper() for x in Path(args.tickers_file).read_text().split() if x.strip()]
    allowed = {r["code"]: r["name"] for r in json.loads((ROOT / "assets/data/asx-tickers.json").read_text())["tickers"]}
    bad = [t for t in tickers if t not in allowed]
    if bad:
        sys.exit(f"not in allowed list: {bad}")
    tickers = sorted(set(tickers))

    post = load_post(args.date)
    editions = {"morning": post}
    if post.get("close"):
        editions["close"] = post["close"]

    closes, anns = {}, {}
    for t in tickers:
        try:
            closes[t] = yahoo_closes(t)
        except Exception as e:  # noqa: BLE001
            print(f"yahoo {t}: {e}", file=sys.stderr); closes[t] = None
        try:
            anns[t] = announcements(t)
        except Exception as e:  # noqa: BLE001
            print(f"asx {t}: {e}", file=sys.stderr); anns[t] = None

    day = dt.date.fromisoformat(args.date)
    out = {
        "schema": "signaletter.watchlist/v1",
        "date": args.date,
        "generated_by": "scripts/build_watchlist_json.py",
        "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "disclaimer": "Information only, not financial advice. Prices delayed and unofficial.",
        "editions": {},
    }
    for scope, ed in editions.items():
        cutoff = dt.datetime.fromisoformat(str(ed["cutoff_local"]))
        quotes = {q["id"]: q for q in (ed.get("snapshot") or {}).get("quotes", [])}
        reviewed = {w["ticker"]: w for w in (ed.get("watchlist") or [])}
        if scope == "morning":
            # previous ASX session = the session of the post's ASX 200 quote, else the latest close before today
            asx = quotes.get("asx200") or {}
            session = asx.get("market_session_date")
            if not session:
                any_c = next((c for c in closes.values() if c), {})
                session = max(d for d in any_c if d < args.date)
            start = dt.datetime.combine(dt.date.fromisoformat(session), dt.time(0, 0), SYD)
            session_word = "on " + dt.date.fromisoformat(session).strftime("%A")
        else:
            session = args.date
            start = dt.datetime.combine(day, dt.time(0, 0), SYD)
            session_word = "on " + day.strftime("%A")
        items = {}
        for t in tickers:
            px = price_block(t, closes.get(t), session, quotes.get(f"wl_{t.lower()}"))
            if t in reviewed:
                r = reviewed[t]
                body = {"note": r["note"], "sources": r.get("sources") or [], "reviewed": True}
                if r.get("next_catalyst"):
                    body["next_catalyst"] = r["next_catalyst"]
            else:
                body = note_from_announcements(t, anns.get(t), start, cutoff, px, session_word)
                body["reviewed"] = False
            items[t] = {"ticker": t, "name": allowed[t], "price": px, **body}
        out["editions"][scope] = {
            "cutoff_local": str(ed["cutoff_local"]), "session_date": session,
            "announcement_window_local": [start.isoformat(), cutoff.isoformat()], "items": items,
        }
    dest = ROOT / "assets" / "issues" / args.date / "watchlist.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {dest}: {len(tickers)} tickers x {list(out['editions'])}")


if __name__ == "__main__":
    main()
