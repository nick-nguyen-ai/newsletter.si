#!/usr/bin/env python3
"""QA gate for newsletter.si Markets v2 posts.

Policy (Nick, 18 Oct 2026): never block the whole issue. Failing claims or
modules are DROPPED (or marked unavailable) and logged in `dropped`; the rest
publishes. Exit codes: 0 = publishable (possibly with drops), 2 = file cannot be
parsed/rendered at all (publish routine must fall back to the previous format).

Usage:
  python3 scripts/qa_markets.py _posts/2026-10-19-markets.md            # report only
  python3 scripts/qa_markets.py --fix _posts/2026-10-19-markets.md      # apply drops in place
  python3 scripts/qa_markets.py --json report.json _posts/*-markets.md

Checks
  schema      JSON-schema validation of the front matter (docs/schemas/markets-post.schema.json)
  placeholder demo/illustrative/TODO/example.org/lorem/"XX" values anywhere
  math        display_value matches value; %/bp/pts changes recompute from value & comparison
  units       yields & spreads use bp, VIX uses pts, prices use %; % sign only on yield values
  time        observation <= cutoff; comparison date < session date; session not in the future
  freshness   freshness_state consistent with expected vs actual session date
  conflict    same-instrument cross-checks differing beyond tolerance -> quote made unavailable
  sources     every card has >=1 http(s) source; comparison tables have >=2 rows
  consensus   consensus requires a named consensus_source (else consensus removed)
  pricing     RBA/Fed pricing 'available' needs a named source and an as-of date
  budget      8-12 story cards (warning only), exactly 3 summary bullets
  language    loaded words / outlet-led sentences (warning, for the reviewer)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys

import yaml

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA = os.path.join(HERE, "..", "docs", "schemas", "markets-post.schema.json")

PLACEHOLDER = re.compile(r"demo_only|illustrative only|illustrative|example\.org|\[todo\]|\btodo\b|lorem ipsum|\bTBD\b|\bXX+\b|placeholder|fictional", re.I)
LOADED = re.compile(r"\b(slammed|blasted|blamed|humiliat\w*|disastrous|blunder|reckless|touted|lashed out|doubled down|falsely|obviously|experts agree|markets punished|money fled|regime propaganda|saved the economy)\b", re.I)
OUTLET_LEAD = re.compile(r"(^|[.!?]\s+)(Reuters|Bloomberg|CNN|Fox( News| Business)?|the WSJ|WSJ|the New York Times|NYT|CNBC|AP) (reports?|says|said|reported)\b")
# Conflict tolerances for same-instrument, same-session cross-checks
TOL = {"pct": 0.05, "bp": 0.03, "pts": 0.25}  # pct = % of value; bp = absolute pct-points; pts = absolute


def split_front_matter(text: str):
    if not text.startswith("---"):
        raise ValueError("no front matter")
    _, fm, body = text.split("---", 2)
    return yaml.safe_load(fm), body


def dump(fm: dict, body: str) -> str:
    return "---\n" + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True, width=1000) + "---" + body


def parse_num(s: str):
    m = re.search(r"[−+-]?\d[\d,]*\.?\d*", s.replace("−", "-"))
    return float(m.group(0).replace(",", "")) if m else None


def iso(s):
    return dt.datetime.fromisoformat(str(s).replace("Z", "+00:00"))


class Report:
    def __init__(self, path):
        self.path, self.errors, self.warnings, self.drops = path, [], [], []

    def err(self, check, msg):
        self.errors.append(f"[{check}] {msg}")

    def warn(self, check, msg):
        self.warnings.append(f"[{check}] {msg}")

    def drop(self, item, reason):
        self.drops.append({"item": item, "reason": reason})


def walk_strings(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_strings(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_strings(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        yield path, obj


def make_unavailable(q, reason):
    keep = {k: q[k] for k in ("id", "display_name", "tier", "instrument_type", "quote_kind", "unit", "currency", "decimals",
                              "change_unit", "expected_session_date", "observation_timezone", "ticker", "note") if k in q}
    keep.update(status="unavailable", freshness_state="unavailable", unavailable_reason=reason,
                provider=q.get("provider"), provider_url=q.get("provider_url"), licence_note=q.get("licence_note"), official=q.get("official"))
    return keep


def check_quote(q, cutoff, rep: Report):
    """Return None if fine, else a reason string (quote will be made unavailable)."""
    if q.get("status") != "ok":
        return None
    v, c = q["value"], q["comparison_value"]
    d = q.get("decimals", 2)
    unit = q.get("unit")
    cu = q.get("change_unit")
    # units
    if q["quote_kind"] in ("yield", "spread") and cu != "bp":
        return f"units: {q['id']} is a {q['quote_kind']} but change_unit={cu} (must be bp)"
    if q["instrument_type"] == "volatility_index" and cu != "pts":
        return f"units: {q['id']} VIX-style index must use index points"
    if q["quote_kind"] not in ("yield", "spread") and cu == "bp":
        return f"units: {q['id']} price quoted with bp change"
    if "%" in q.get("display_value", "") and unit != "%":
        return f"units: {q['id']} display shows % but unit={unit}"
    # display value
    dv = parse_num(q["display_value"])
    if dv is None or abs(dv - round(v, d if unit != "bp" else 0)) > 10 ** (-d) * 0.51 + 1e-9:
        return f"math: {q['id']} display_value {q['display_value']} != value {v}"
    # change math
    disp = parse_num(q["display_change"].replace("last move", ""))
    if cu == "bp":
        bp = (v - c) * (1 if unit == "bp" else 100)
        if abs(bp - q.get("change_bp", 1e9)) > 0.15:
            return f"math: {q['id']} change_bp {q.get('change_bp')} != recomputed {bp:.2f}"
        if disp is None or abs(disp - round(bp)) > 0.51:
            return f"math: {q['id']} display_change {q['display_change']} != {bp:.1f} bp"
    else:
        pct = 100 * (v / c - 1)
        if abs(pct - q.get("change_pct", 1e9)) > 0.011:
            return f"math: {q['id']} change_pct {q.get('change_pct')} != recomputed {pct:.3f}"
        if cu == "pts":
            if disp is None or abs(disp - (v - c)) > 10 ** (-d) * 0.51 + 1e-9:
                return f"math: {q['id']} display_change {q['display_change']} != {v - c:.{d}f} pts"
        else:
            if disp is None or abs(disp - pct) > 0.051 + (0.005 if q['instrument_type'] == 'fx' else 0):
                return f"math: {q['id']} display_change {q['display_change']} != {pct:.2f}%"
    # weekly
    if "week_comparison_value" in q:
        wv = q["week_comparison_value"]
        if cu == "bp" and "week_change_bp" in q and abs((v - wv) * 100 - q["week_change_bp"]) > 0.15:
            return f"math: {q['id']} week_change_bp mismatch"
        if cu == "pct" and "week_change_pct" in q and abs(100 * (v / wv - 1) - q["week_change_pct"]) > 0.011:
            return f"math: {q['id']} week_change_pct mismatch"
    # time
    obs = iso(q["observation_timestamp_utc"])
    if cutoff and obs > cutoff:
        return f"time: {q['id']} observed {obs} after cutoff {cutoff}"
    sess = dt.date.fromisoformat(q["market_session_date"])
    if dt.date.fromisoformat(q["comparison_date"]) >= sess:
        return f"time: {q['id']} comparison_date not before session date"
    exp = q.get("expected_session_date")
    if exp:
        exp = dt.date.fromisoformat(exp)
        if sess > exp:
            return f"time: {q['id']} session {sess} later than expected {exp}"
        if sess < exp and q["freshness_state"] == "latest_official_close":
            return f"freshness: {q['id']} labelled latest close but session {sess} < expected {exp}"
        if sess == exp and q["freshness_state"] in ("stale", "scheduled_lag"):
            rep.warn("freshness", f"{q['id']} labelled {q['freshness_state']} but has the expected session")
    # licence/provenance
    if not q.get("licence_note") or not q.get("provider_url", "").startswith("http"):
        return f"provenance: {q['id']} missing licence note or provider URL"
    if q.get("official") is False and q.get("source_label") != "delayed, unofficial":
        return f"provenance: {q['id']} unofficial provider must be labelled 'delayed, unofficial'"
    # conflicts
    for ck in q.get("cross_checks", []) or []:
        if ck.get("session_date") != q["market_session_date"]:
            continue
        diff = abs(ck["value"] - v)
        tol = TOL.get(cu, 0.05)
        bad = diff / abs(v) * 100 > tol if cu == "pct" else diff > tol
        if bad:
            return (f"conflict: {q['id']} {q['provider']}={v} vs {ck['provider']}={ck['value']} for the same "
                    f"instrument and session ({q['market_session_date']}); held until resolved")
    return None


def qa(fm: dict, rep: Report, fix: bool):
    # placeholders (hard: drop the containing card/quote; if in summary, error)
    for path, s in walk_strings(fm):
        if path.endswith(("licence_note", "unavailable_reason", "reason")):
            continue
        if PLACEHOLDER.search(s):
            rep.err("placeholder", f"{path}: {s[:80]!r}")
    if jsonschema is not None:
        schema = json.load(open(SCHEMA))
        fm_json = json.loads(json.dumps(fm, default=str))
        for e in sorted(jsonschema.Draft202012Validator(schema).iter_errors(fm_json), key=lambda e: list(e.path)):
            rep.err("schema", f"{'/'.join(map(str, e.path)) or '(root)'}: {e.message[:160]}")
    else:
        rep.warn("schema", "jsonschema not installed; schema validation skipped")

    cutoff = iso(fm["snapshot"]["cutoff_utc"]) if fm.get("snapshot", {}).get("cutoff_utc") else None
    quotes = fm.get("snapshot", {}).get("quotes", [])
    for i, q in enumerate(quotes):
        reason = check_quote(q, cutoff, rep)
        if reason:
            rep.err(reason.split(":")[0], reason)
            rep.drop(f"snapshot:{q.get('id')}", reason)
            if fix:
                quotes[i] = make_unavailable(q, reason)

    # cards
    n_cards = 0
    for sec in fm.get("sections", []):
        keep = []
        for card in sec.get("cards", []):
            cid = f"{sec['id']}/{card.get('id')}"
            text = json.dumps(card, ensure_ascii=False)
            if PLACEHOLDER.search(text):
                rep.drop(f"card:{cid}", "placeholder/demo text")
                continue
            srcs = [s for s in card.get("sources", []) if str(s.get("url", "")).startswith(("http://", "https://"))]
            if not srcs:
                rep.err("sources", f"{cid} has no valid source")
                rep.drop(f"card:{cid}", "no verifiable source")
                continue
            comp = card.get("comparison")
            if comp is not None and len(comp.get("rows", [])) < 2:
                rep.err("sources", f"{cid} comparison has <2 rows")
                rep.drop(f"comparison:{cid}", "comparison table needs at least two sourced rows")
                if fix:
                    card.pop("comparison")
            for path, s in walk_strings(card):
                if LOADED.search(s):
                    rep.warn("language", f"{cid}.{path}: loaded word {LOADED.search(s).group(0)!r}")
                if OUTLET_LEAD.search(s):
                    rep.warn("language", f"{cid}.{path}: sentence led by outlet name")
            keep.append(card)
        if fix:
            sec["cards"] = keep
        n_cards += len(keep)
    if not 8 <= n_cards <= 12:
        rep.warn("budget", f"{n_cards} story cards (target 8-12; no filler)")
    if len(fm.get("summary", [])) != 3:
        rep.err("budget", "summary must have exactly 3 bullets")

    # calendar consensus
    for i, row in enumerate(fm.get("calendar", []) or []):
        if row.get("consensus") and not row.get("consensus_source"):
            rep.err("consensus", f"calendar[{i}] consensus without named source")
            rep.drop(f"calendar[{i}].consensus", "consensus without a named source")
            if fix:
                row.pop("consensus")
    # pricing
    for cb in ("rba", "fed"):
        p = (fm.get("rates") or {}).get(cb)
        if p and p.get("status") == "available" and not (p.get("source", {}).get("url") and p.get("as_of")):
            rep.err("pricing", f"{cb} pricing marked available without named source/as-of")
            rep.drop(f"rates:{cb}", "market pricing without a named, dated source")
            if fix:
                fm["rates"][cb] = {"status": "unavailable", "forecasts": p.get("forecasts", [])}
    for path, s in walk_strings({"summary": fm.get("summary", [])}):
        if LOADED.search(s):
            rep.warn("language", f"{path}: loaded word {LOADED.search(s).group(0)!r}")

    if fix and rep.drops:
        existing = fm.setdefault("dropped", [])
        seen = {(d["item"], d["reason"]) for d in existing}
        for d in rep.drops:
            if (d["item"], d["reason"]) not in seen:
                existing.append(d)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--fix", action="store_true")
    ap.add_argument("--json")
    args = ap.parse_args(argv)
    out, worst = [], 0
    for f in args.files:
        rep = Report(f)
        try:
            fm, body = split_front_matter(open(f, encoding="utf-8").read())
            if fm.get("format") != "markets-v2":
                print(f"SKIP {f} (not markets-v2)")
                continue
            qa(fm, rep, args.fix)
            if args.fix:
                # re-validate after drops; anything still failing schema is fatal
                rep2 = Report(f)
                qa(fm, rep2, False)
                if any(e.startswith("[schema]") for e in rep2.errors):
                    rep.err("fatal", "schema still invalid after fixes")
                    worst = 2
                open(f, "w", encoding="utf-8").write(dump(fm, body))
        except Exception as e:  # noqa: BLE001
            rep.err("fatal", f"cannot parse: {e}")
            worst = 2
        status = "FATAL" if any(e.startswith("[fatal]") for e in rep.errors) else ("PASS_WITH_DROPS" if rep.drops or rep.errors else "PASS")
        print(f"{status} {f}: {len(rep.errors)} errors, {len(rep.warnings)} warnings, {len(rep.drops)} drops")
        for e in rep.errors:
            print("  ERROR", e)
        for w in rep.warnings:
            print("  warn ", w)
        out.append({"file": f, "status": status, "errors": rep.errors, "warnings": rep.warnings, "drops": rep.drops})
    if args.json:
        json.dump(out, open(args.json, "w"), indent=2)
    return worst


if __name__ == "__main__":
    sys.exit(main())
