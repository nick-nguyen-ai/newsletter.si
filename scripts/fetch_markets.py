#!/usr/bin/env python3
"""Deterministic market-data collector for signaletter.si Markets v2.

Builds the `snapshot` block of a Markets post (dashboard quotes + watchlist
quotes) with full provenance. No LLM involved; no numbers are ever guessed.

Source policy (Nick, 18 Oct 2026):
  official free sources first (RBA, FRED/US Treasury, ABS, Cboe VIX CSV); otherwise Yahoo
  Finance labelled "delayed, unofficial". Provider + licence note per metric.
  If a value can't be verified for the target session it is `unavailable`.

Usage:
  python3 scripts/fetch_markets.py --issue-date 2026-10-19 --edition weekday \
      [--cutoff 07:30] [--out snapshot.json] [--yaml]

Historical (backfill) mode is the same command with a past --issue-date: every
series is cut at the cutoff, so nothing published after the session is used for
the value itself (retrieval vintage is recorded honestly as today's date).
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import sys
import time
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

SYD = ZoneInfo("Australia/Sydney")
NY = ZoneInfo("America/New_York")
UTC = dt.timezone.utc
UA = "Mozilla/5.0 (X11; Linux x86_64) signaletter.si-fetch/1.0"

LIC = {
    "rba": "RBA statistical tables, CC BY 4.0 (attribution: Reserve Bank of Australia).",
    "fred_public": "FRED (St. Louis Fed); underlying series is US-government public data.",
    "fred_cboe": "FRED series VIXCLS; source Cboe. Cite Cboe/FRED; third-party data, not for bulk redistribution.",
    "cboe": "Cboe Global Markets daily VIX history CSV; cite Cboe; personal non-commercial display of single closes.",
    "treasury": "US Treasury daily par yield curve; US-government public data.",
    "yahoo": "Yahoo Finance chart data: delayed, unofficial; Yahoo terms restrict redistribution. Shown as a cited single quote only.",
    "fred_eia": "FRED DCOILBRENTEU; source US EIA (public data). Spot assessment, published with a lag of several days.",
}

# ---------------------------------------------------------------- HTTP

def get(url: str, retries: int = 3, pause: float = 4.0) -> str:
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read().decode("utf-8-sig", errors="replace")
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(pause * (i + 1))
    raise RuntimeError(f"fetch failed {url}: {last}")


# ---------------------------------------------------------------- series loaders
# Each loader returns a list of (session_date: date, value: float, obs_utc: datetime|None)

_cache: dict = {}


def fred(series_id: str):
    key = ("fred", series_id)
    if key not in _cache:
        txt = get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&cosd=2025-06-01")
        rows = []
        for r in csv.reader(io.StringIO(txt)):
            if len(r) < 2 or not r[0][:4].isdigit() or r[1] in ("", "."):
                continue
            rows.append((dt.date.fromisoformat(r[0]), float(r[1]), None))
        _cache[key] = rows
    return _cache[key]


def rba(table: str, series_id: str):
    key = ("rba", table)
    if key not in _cache:
        _cache[key] = list(csv.reader(io.StringIO(get(f"https://www.rba.gov.au/statistics/tables/csv/{table}-data.csv"))))
    rows = _cache[key]
    sid_row = next(r for r in rows if r and r[0] == "Series ID")
    col = sid_row.index(series_id)
    out = []
    for r in rows:
        if r and len(r) > col and r[0][:2].isdigit() and r[col].strip():
            out.append((dt.datetime.strptime(r[0], "%d-%b-%Y").date(), float(r[col]), None))
    return out


def treasury(col_name: str):
    key = ("ust",)
    if key not in _cache:
        rows = []
        for yr in (dt.date.today().year - 1, dt.date.today().year):
            txt = get("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
                      f"daily-treasury-rates.csv/{yr}/all?type=daily_treasury_yield_curve&field_tdr_date_value={yr}&page&_format=csv")
            rows += list(csv.DictReader(io.StringIO(txt)))
        _cache[key] = rows
    out = []
    for r in _cache[key]:
        v = r.get(col_name)
        if v:
            out.append((dt.datetime.strptime(r["Date"], "%m/%d/%Y").date(), float(v), None))
    return sorted(out)


def yahoo(symbol: str):
    key = ("yahoo", symbol)
    if key not in _cache:
        time.sleep(3)  # be polite: bursts trigger HTTP 429
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?range=3mo&interval=1d"
        d = json.loads(get(url, retries=4, pause=8))["chart"]["result"][0]
        tz = ZoneInfo(d["meta"].get("exchangeTimezoneName") or "UTC")
        ts = d.get("timestamp") or []
        closes = d["indicators"]["quote"][0]["close"]
        by_day: dict = {}
        for t, c in zip(ts, closes):
            if c is None:
                continue
            local = dt.datetime.fromtimestamp(t, UTC).astimezone(tz)
            by_day[local.date()] = (local.date(), float(c), dt.datetime.fromtimestamp(t, UTC))  # last bar per local day wins
        _cache[key] = (sorted(by_day.values()), d["meta"])
    return _cache[key][0]


def cboe_vix(_ref: str = "VIX"):
    """Cboe free daily VIX history CSV (CLOSE column). Dates are US session dates."""
    key = ("cboe", "VIX")
    if key not in _cache:
        # Official free history; cdn.cboe.com may 307 to cdn-api.cboe.com.
        txt = get("https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv")
        rows = []
        for r in csv.DictReader(io.StringIO(txt)):
            d_raw = (r.get("DATE") or r.get("Date") or "").strip()
            c_raw = (r.get("CLOSE") or r.get("Close") or "").strip()
            if not d_raw or not c_raw:
                continue
            rows.append((dt.datetime.strptime(d_raw, "%m/%d/%Y").date(), float(c_raw), None))
        _cache[key] = sorted(rows)
    return _cache[key]


# ---------------------------------------------------------------- sessions

def expected_session(cutoff_utc: dt.datetime, tz: ZoneInfo, close_hm: tuple[int, int]) -> dt.date:
    """Latest weekday whose local close time is at or before the cutoff (holidays not modelled)."""
    local = cutoff_utc.astimezone(tz)
    d = local.date()
    for _ in range(10):
        close = dt.datetime(d.year, d.month, d.day, *close_hm, tzinfo=tz)
        if d.weekday() < 5 and close <= cutoff_utc:
            return d
        d -= dt.timedelta(days=1)
    return d


MARKETS = {
    "ASX": (SYD, (16, 10)),
    "RBA_FX": (SYD, (16, 0)),
    "RBA_YLD": (SYD, (16, 30)),
    "US": (NY, (16, 0)),
    "US_YLD": (NY, (15, 30)),
    "COMEX": (NY, (13, 30)),
    "NYMEX": (NY, (14, 30)),
    "EIA": (NY, (14, 30)),
}

# metric specs: candidates are tried in order; first candidate that has the
# expected session wins, otherwise the freshest candidate is used and labelled.
METRICS = [
    dict(id="asx200", display_name="S&P/ASX 200", tier="primary", instrument_type="equity_index", quote_kind="index_close",
         unit="pts", currency="AUD", decimals=1, change="pct", market="ASX", lag_days=0,
         candidates=[("yahoo", "^AXJO", "Yahoo Finance (^AXJO)", "https://finance.yahoo.com/quote/%5EAXJO/", "yahoo")]),
    dict(id="sp500", display_name="S&P 500", tier="primary", instrument_type="equity_index", quote_kind="index_close",
         unit="pts", currency="USD", decimals=1, change="pct", market="US", lag_days=0,
         candidates=[("yahoo", "^GSPC", "Yahoo Finance (^GSPC)", "https://finance.yahoo.com/quote/%5EGSPC/", "yahoo")],
         cross_check=("fred", "SP500", "FRED SP500 (S&P Dow Jones Indices)")),
    dict(id="audusd", display_name="AUD/USD", tier="primary", instrument_type="fx", quote_kind="spot",
         unit="USD", currency="USD", decimals=4, change="pct", market="RBA_FX", lag_days=1,
         note="RBA 4pm Sydney rate (WM/Reuters); not the overnight move.",
         candidates=[("rba", ("f11.1", "FXRUSD"), "RBA F11.1 (4pm AEST/AEDT)", "https://www.rba.gov.au/statistics/tables/#exchange-rates", "rba")]),
    dict(id="au10y", display_name="Australia 10Y", tier="primary", instrument_type="government_bond", quote_kind="yield",
         unit="%", currency="AUD", decimals=2, change="bp", market="RBA_YLD", lag_days=4,
         note="RBA interpolated 10-year yield; published with a lag of about two business days.",
         candidates=[("rba", ("f2", "FCMYGBAG10D"), "RBA F2 capital market yields", "https://www.rba.gov.au/statistics/tables/#interest-rates", "rba")]),
    dict(id="brent_spot", display_name="Brent (spot)", tier="primary", instrument_type="commodity", quote_kind="spot",
         unit="USD/bbl", currency="USD", decimals=2, change="pct", market="EIA", lag_days=6,
         note="EIA Europe Brent spot assessment via FRED. Not the futures price quoted in most news reports.",
         candidates=[("fred", "DCOILBRENTEU", "FRED DCOILBRENTEU (EIA)", "https://fred.stlouisfed.org/series/DCOILBRENTEU", "fred_eia")]),
    dict(id="vix", display_name="VIX", tier="primary", instrument_type="volatility_index", quote_kind="index_close",
         unit="pts", currency="", decimals=2, change="pts", market="US", lag_days=0,
         candidates=[("cboe", "VIX", "Cboe VIX History", "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv", "cboe"),
                     ("fred", "VIXCLS", "FRED VIXCLS (Cboe)", "https://fred.stlouisfed.org/series/VIXCLS", "fred_cboe"),
                     ("yahoo", "^VIX", "Yahoo Finance (^VIX)", "https://finance.yahoo.com/quote/%5EVIX/", "yahoo")]),
    # ---- expanded
    dict(id="nasdaq", display_name="Nasdaq Composite", tier="expanded", instrument_type="equity_index", quote_kind="index_close",
         unit="pts", currency="USD", decimals=1, change="pct", market="US", lag_days=0,
         candidates=[("yahoo", "^IXIC", "Yahoo Finance (^IXIC)", "https://finance.yahoo.com/quote/%5EIXIC/", "yahoo")],
         cross_check=("fred", "NASDAQCOM", "FRED NASDAQCOM (Nasdaq)")),
    dict(id="au2y", display_name="Australia 2Y", tier="expanded", instrument_type="government_bond", quote_kind="yield",
         unit="%", currency="AUD", decimals=2, change="bp", market="RBA_YLD", lag_days=4,
         candidates=[("rba", ("f2", "FCMYGBAG2D"), "RBA F2 capital market yields", "https://www.rba.gov.au/statistics/tables/#interest-rates", "rba")]),
    dict(id="us10y", display_name="US 10Y", tier="expanded", instrument_type="government_bond", quote_kind="yield",
         unit="%", currency="USD", decimals=2, change="bp", market="US_YLD", lag_days=1,
         candidates=[("fred", "DGS10", "FRED DGS10 (US Treasury)", "https://fred.stlouisfed.org/series/DGS10", "fred_public"),
                     ("ust", "10 Yr", "US Treasury par yield curve", "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve", "treasury")]),
    dict(id="us2y", display_name="US 2Y", tier="expanded", instrument_type="government_bond", quote_kind="yield",
         unit="%", currency="USD", decimals=2, change="bp", market="US_YLD", lag_days=1,
         candidates=[("fred", "DGS2", "FRED DGS2 (US Treasury)", "https://fred.stlouisfed.org/series/DGS2", "fred_public"),
                     ("ust", "2 Yr", "US Treasury par yield curve", "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve", "treasury")]),
    dict(id="brent_fut", display_name="Brent (futures)", tier="expanded", instrument_type="commodity", quote_kind="futures_last",
         unit="USD/bbl", currency="USD", decimals=2, change="pct", market="NYMEX", lag_days=0,
         note="Yahoo BZ=F: front-month Brent last-day financial futures (NYMEX), daily close. Differs from the spot assessment.",
         candidates=[("yahoo", "BZ=F", "Yahoo Finance (BZ=F)", "https://finance.yahoo.com/quote/BZ%3DF/", "yahoo")]),
    dict(id="gold_fut", display_name="Gold (COMEX futures)", tier="expanded", instrument_type="commodity", quote_kind="futures_last",
         unit="USD/oz", currency="USD", decimals=1, change="pct", market="COMEX", lag_days=0,
         note="Yahoo GC=F: active COMEX gold futures contract, not the spot or LBMA price.",
         candidates=[("yahoo", "GC=F", "Yahoo Finance (GC=F)", "https://finance.yahoo.com/quote/GC%3DF/", "yahoo")]),
    dict(id="rba_cash", display_name="RBA cash rate target", tier="expanded", instrument_type="policy_rate", quote_kind="yield",
         unit="%", currency="AUD", decimals=2, change="bp", market="RBA_FX", lag_days=4, change_vs="last_change",
         candidates=[("rba", ("f1", "FIRMMCRTD"), "RBA F1 cash rate target", "https://www.rba.gov.au/statistics/cash-rate/", "rba")]),
    # placeholders that are honestly unavailable from free/permitted sources
    dict(id="asx200_fut", display_name="ASX SPI 200 futures", tier="expanded", instrument_type="equity_index_future", quote_kind="futures_last",
         unit="pts", currency="AUD", decimals=0, change="pct", market="ASX", lag_days=0, candidates=[],
         unavailable_reason="No free, permitted feed for ASX 24 SPI 200 futures (licensed exchange data)."),
    dict(id="iron_ore", display_name="Iron ore 62% Fe", tier="expanded", instrument_type="commodity", quote_kind="futures_last",
         unit="USD/t", currency="USD", decimals=2, change="pct", market="US", lag_days=0, candidates=[],
         unavailable_reason="No free, permitted daily benchmark (SGX/Platts are licensed); the only free series (IMF via FRED) is monthly."),
]

WEEKLY = False
BACKFILL = False

WATCHLIST_DEFAULT = [("ZIP", "Zip Co"), ("CSL", "CSL"), ("FLT", "Flight Centre"), ("IEL", "IDP Education")]


def load_series(kind, ref):
    if kind == "fred":
        return fred(ref)
    if kind == "rba":
        return rba(*ref)
    if kind == "ust":
        return treasury(ref)
    if kind == "yahoo":
        return yahoo(ref)
    if kind == "cboe":
        return cboe_vix(ref)
    raise ValueError(kind)


def fmt(v: float, decimals: int) -> str:
    return f"{v:,.{decimals}f}"


def signed(v: float, decimals: int) -> str:
    s = f"{abs(v):,.{decimals}f}"
    return ("+" if v > 0 else "−" if v < 0 else "±") + s


def build_quote(spec: dict, cutoff_utc: dt.datetime, retrieved: str) -> dict:
    tz, close_hm = MARKETS[spec["market"]]
    exp = expected_session(cutoff_utc, tz, close_hm)
    base = {k: spec.get(k) for k in ("id", "display_name", "tier", "instrument_type", "quote_kind", "unit", "currency", "decimals")}
    base.update(change_unit=spec["change"], expected_session_date=exp.isoformat(), observation_timezone=str(tz))
    if spec.get("note"):
        base["note"] = spec["note"]
    if not spec["candidates"]:
        base.update(status="unavailable", freshness_state="unavailable", unavailable_reason=spec["unavailable_reason"],
                    provider=None, provider_url=None, licence_note=None, official=None)
        return base
    errors, best = [], None
    for kind, ref, provider, url, lic in spec["candidates"]:
        try:
            rows = [r for r in load_series(kind, ref)
                    if dt.datetime(r[0].year, r[0].month, r[0].day, *close_hm, tzinfo=tz) <= cutoff_utc]
        except Exception as e:  # noqa: BLE001
            errors.append(f"{provider}: {e}")
            continue
        if len(rows) < 2:
            errors.append(f"{provider}: not enough observations before cutoff")
            continue
        cand = (rows, kind, provider, url, lic)
        if rows[-1][0] >= exp:
            best = cand
            break
        if best is None or rows[-1][0] > best[0][-1][0]:
            best = cand
    if best is None:
        base.update(status="unavailable", freshness_state="unavailable", provider=None, provider_url=None, licence_note=None,
                    official=None, unavailable_reason="; ".join(errors) or "no data")
        return base
    rows, kind, provider, url, lic = best
    obs_d, val, obs_ts = rows[-1]
    if spec.get("change_vs") == "last_change":
        prev = next((r for r in reversed(rows) if r[1] != val), rows[-2])
    else:
        prev = rows[-2]
    cmp_d, cmp_v, _ = prev
    lag = (exp - obs_d).days
    if obs_d >= exp:
        fresh = "latest_official_close"
    elif lag <= spec.get("lag_days", 0) + 2 and spec.get("lag_days", 0) > 0:
        fresh = "scheduled_lag"
    else:
        fresh = "stale"
    if obs_ts is None:
        obs_ts = dt.datetime(obs_d.year, obs_d.month, obs_d.day, *close_hm, tzinfo=tz).astimezone(UTC)
    d = spec["decimals"]
    q = dict(base)
    q.update(
        status="ok", provider=provider, provider_url=url, licence_note=LIC[lic], official=(kind != "yahoo"),
        source_label=("delayed, unofficial" if kind == "yahoo" else "official"),
        value=round(val, 6), display_value=fmt(val, d) + ("%" if spec["unit"] == "%" else ""),
        market_session_date=obs_d.isoformat(), observation_timestamp_utc=obs_ts.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        comparison_date=cmp_d.isoformat(), comparison_value=round(cmp_v, 6),
        freshness_state=fresh,
        source_vintage=f"retrieved {retrieved}" + (" (historical backfill: value cut at the issue cutoff, retrieved later)" if BACKFILL else ""),
    )
    diff = val - cmp_v
    if spec["change"] == "bp":
        q["change_bp"] = round(diff * 100, 1)
        q["display_change"] = signed(round(diff * 100), 0) + " bp"
    elif spec["change"] == "pts":
        q["change_abs"] = round(diff, d)
        q["change_pct"] = round(100 * (val / cmp_v - 1), 2)
        q["display_change"] = signed(diff, d) + " pts"
    else:
        q["change_abs"] = round(diff, d)
        q["change_pct"] = round(100 * (val / cmp_v - 1), 2)
        q["display_change"] = signed(100 * (val / cmp_v - 1), 1 if spec["instrument_type"] != "fx" else 2) + "%"
    if spec.get("change_vs") == "last_change":
        q["display_change"] = "last move " + q["display_change"] + " (" + dt.date.fromisoformat(next(
            r[0] for r in rows if r[0] > cmp_d).isoformat()).strftime("%-d %b") + ")"
    if WEEKLY and spec.get("change_vs") != "last_change":
        wk = [r for r in rows if r[0] <= obs_d - dt.timedelta(days=7)]
        if wk:
            wd, wv, _ = wk[-1]
            q["week_comparison_date"] = wd.isoformat()
            q["week_comparison_value"] = round(wv, 6)
            if spec["change"] == "bp":
                q["week_change_bp"] = round((val - wv) * 100, 1)
                q["display_week_change"] = signed(round((val - wv) * 100), 0) + " bp wk"
            elif spec["change"] == "pts":
                q["week_change_abs"] = round(val - wv, d)
                q["display_week_change"] = signed(val - wv, d) + " pts wk"
            else:
                q["week_change_pct"] = round(100 * (val / wv - 1), 2)
                q["display_week_change"] = signed(100 * (val / wv - 1), 1) + "% wk"
    if spec.get("cross_check"):
        ck, cref, cprov = spec["cross_check"]
        try:
            m = {r[0]: r[1] for r in load_series(ck, cref)}
            if obs_d in m:
                q["cross_checks"] = [{"provider": cprov, "value": m[obs_d], "session_date": obs_d.isoformat()}]
        except Exception:  # noqa: BLE001
            pass
    return q


def watch_quote(ticker: str, name: str, cutoff_utc: dt.datetime, retrieved: str) -> dict:
    spec = dict(id=f"wl_{ticker.lower()}", display_name=f"{ticker} · {name}", tier="watchlist", instrument_type="equity",
                quote_kind="index_close", unit="AUD", currency="AUD", decimals=3 if ticker == "ZIP" else 2, change="pct",
                market="ASX", lag_days=0,
                candidates=[("yahoo", f"{ticker}.AX", f"Yahoo Finance ({ticker}.AX)", f"https://finance.yahoo.com/quote/{ticker}.AX/", "yahoo")])
    q = build_quote(spec, cutoff_utc, retrieved)
    q["quote_kind"] = "close"
    q["ticker"] = ticker
    return q


def load_watchlist(path: str | None):
    if path:
        try:
            with open(path, newline="") as f:
                return [(r["ticker"].strip(), r["name"].strip()) for r in csv.DictReader(f) if r.get("ticker")]
        except FileNotFoundError:
            pass
    return WATCHLIST_DEFAULT


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--issue-date", required=True)
    ap.add_argument("--edition", choices=["weekday", "weekend"], required=True)
    ap.add_argument("--cutoff", default="07:30", help="local Sydney HH:MM")
    ap.add_argument("--watchlist", default="_data/watchlist.csv")
    ap.add_argument("--out")
    ap.add_argument("--backfill", action="store_true", help="re-rendering a past issue")
    args = ap.parse_args(argv)
    global WEEKLY, BACKFILL
    WEEKLY = args.edition == "weekend"
    BACKFILL = args.backfill
    d = dt.date.fromisoformat(args.issue_date)
    hh, mm = map(int, args.cutoff.split(":"))
    cutoff = dt.datetime(d.year, d.month, d.day, hh, mm, tzinfo=SYD).astimezone(UTC)
    retrieved = dt.datetime.now(UTC).strftime("%Y-%m-%d %H:%MZ")
    quotes, dropped = [], []
    for spec in METRICS:
        q = build_quote(spec, cutoff, retrieved)
        quotes.append(q)
        if q["status"] != "ok":
            dropped.append({"item": f"snapshot:{q['id']}", "reason": q.get("unavailable_reason", "unavailable")})
    for t, n in load_watchlist(args.watchlist):
        q = watch_quote(t, n, cutoff, retrieved)
        quotes.append(q)
        if q["status"] != "ok":
            dropped.append({"item": f"watchlist:{t}", "reason": q.get("unavailable_reason", "unavailable")})
    # derived: AU 10Y-2Y curve (only when both legs share a session date)
    a10 = next(q for q in quotes if q["id"] == "au10y")
    a2 = next(q for q in quotes if q["id"] == "au2y")
    curve = dict(id="au_curve", display_name="AU 10Y–2Y curve", tier="expanded", instrument_type="spread", quote_kind="spread",
                 unit="bp", currency="AUD", decimals=0, change_unit="bp", observation_timezone=str(SYD),
                 expected_session_date=a10.get("expected_session_date"))
    if a10["status"] == "ok" and a2["status"] == "ok" and a10["market_session_date"] == a2["market_session_date"] \
            and a10["comparison_date"] == a2["comparison_date"]:
        v = round((a10["value"] - a2["value"]) * 100, 1)
        pv = round((a10["comparison_value"] - a2["comparison_value"]) * 100, 1)
        curve.update(status="ok", provider="Derived from RBA F2 (10Y minus 2Y)", provider_url=a10["provider_url"],
                     licence_note=LIC["rba"], official=True, source_label="official", value=v, display_value=f"{v:+.0f} bp",
                     market_session_date=a10["market_session_date"], observation_timestamp_utc=a10["observation_timestamp_utc"],
                     comparison_date=a10["comparison_date"], comparison_value=pv, change_bp=round(v - pv, 1),
                     display_change=signed(round(v - pv), 0) + " bp", freshness_state=a10["freshness_state"],
                     source_vintage=a10["source_vintage"])
    else:
        curve.update(status="unavailable", freshness_state="unavailable", unavailable_reason="AU 2Y and 10Y not available for the same session.")
    quotes.insert([q["id"] for q in quotes].index("au2y") + 1, curve)
    snap = {
        "generated_by": "scripts/fetch_markets.py",
        "retrieved_at_utc": retrieved,
        "issue_date": d.isoformat(),
        "edition": args.edition,
        "backfill": BACKFILL,
        "cutoff_utc": cutoff.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cutoff_local": dt.datetime(d.year, d.month, d.day, hh, mm, tzinfo=SYD).isoformat(),
        "quotes": quotes,
        "dropped": dropped,
    }
    js = json.dumps(snap, indent=2, ensure_ascii=False)
    if args.out:
        with open(args.out, "w") as f:
            f.write(js + "\n")
    else:
        print(js)


if __name__ == "__main__":
    main()
