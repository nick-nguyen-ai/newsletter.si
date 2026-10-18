#!/usr/bin/env python3
"""Acceptance tests for scripts/qa_markets.py (spec K: the QA must reject a
fabricated number, a conflicting same-contract quote, a biased/unsupported
claim and an invented market probability). Run: python3 scripts/tests/test_qa_markets.py"""
import copy
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import qa_markets as qa  # noqa: E402

POST = sorted(glob.glob(os.path.join(HERE, "..", "..", "_posts", "*-markets.md")))[-1]
BASE, _ = qa.split_front_matter(open(POST, encoding="utf-8").read())


def run(fm, fix=True):
    rep = qa.Report("test")
    qa.qa(fm, rep, fix)
    return rep


def quote(fm, qid):
    return next(q for q in fm["snapshot"]["quotes"] if q["id"] == qid)


def test_clean_post_passes():
    rep = run(copy.deepcopy(BASE), fix=False)
    assert not rep.errors, rep.errors


def test_fabricated_number_rejected():
    fm = copy.deepcopy(BASE)
    quote(fm, "asx200")["display_value"] = "9,999.9"  # number not backed by the record
    rep = run(fm)
    assert any("math" in e for e in rep.errors), rep.errors
    assert quote(fm, "asx200")["status"] == "unavailable"
    assert any(d["item"] == "snapshot:asx200" for d in fm["dropped"])


def test_bad_change_math_rejected():
    fm = copy.deepcopy(BASE)
    quote(fm, "us10y")["change_bp"] = 5.0
    rep = run(fm)
    assert any("change_bp" in e for e in rep.errors), rep.errors


def test_percent_used_for_yield_rejected():
    fm = copy.deepcopy(BASE)
    quote(fm, "au10y")["change_unit"] = "pct"
    rep = run(fm)
    assert any(e.startswith("[units]") for e in rep.errors), rep.errors


def test_same_instrument_conflict_held():
    fm = copy.deepcopy(BASE)
    q = quote(fm, "sp500")
    q["cross_checks"] = [{"provider": "Second feed", "value": q["value"] * 1.02, "session_date": q["market_session_date"]}]
    rep = run(fm)
    assert any(e.startswith("[conflict]") for e in rep.errors), rep.errors
    assert quote(fm, "sp500")["status"] == "unavailable"


def test_observation_after_cutoff_rejected():
    fm = copy.deepcopy(BASE)
    quote(fm, "vix")["observation_timestamp_utc"] = "2099-01-01T00:00:00Z"
    rep = run(fm)
    assert any(e.startswith("[time]") for e in rep.errors), rep.errors


def test_demo_placeholder_rejected():
    fm = copy.deepcopy(BASE)
    fm["sections"][0]["cards"][0]["headline"] = "ILLUSTRATIVE ONLY example headline"
    rep = run(fm)
    assert any(e.startswith("[placeholder]") for e in rep.errors), rep.errors
    assert all(c["headline"].find("ILLUSTRATIVE") < 0 for s in fm["sections"] for c in s["cards"])


def test_invented_probability_rejected():
    fm = copy.deepcopy(BASE)
    fm["rates"]["rba"] = {"status": "available", "summary": "62% chance of a hike"}  # no source, no as-of
    rep = run(fm)
    assert any(e.startswith("[pricing]") or e.startswith("[schema]") for e in rep.errors), rep.errors
    assert fm["rates"]["rba"]["status"] == "unavailable"


def test_unsourced_claim_dropped():
    fm = copy.deepcopy(BASE)
    card = copy.deepcopy(fm["sections"][-1]["cards"][0])
    card["id"] = "unsourced"
    card["sources"] = [{"label": "Somebody", "url": "not-a-url"}]
    fm["sections"][-1]["cards"].append(card)
    run(fm)
    assert all(c["id"] != "unsourced" for c in fm["sections"][-1]["cards"])


def test_consensus_needs_named_source():
    fm = copy.deepcopy(BASE)
    fm["calendar"][0]["consensus"] = "4.6%"
    rep = run(fm)
    assert "consensus" not in fm["calendar"][0], rep.errors


def test_loaded_language_flagged():
    fm = copy.deepcopy(BASE)
    fm["sections"][-1]["cards"][0]["what_happened"] += " Critics slammed the move. Reuters reports more."
    rep = run(fm, fix=False)
    assert sum(w.startswith("[language]") for w in rep.warnings) >= 2, rep.warnings


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            try:
                fn()
                print("ok  ", name)
            except AssertionError as e:
                fails += 1
                print("FAIL", name, e)
    print(f"{fails} failed")
    sys.exit(1 if fails else 0)
