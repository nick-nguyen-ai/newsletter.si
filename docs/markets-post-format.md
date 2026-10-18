# Markets post front-matter format (Markets v2)

Markets issues ship as **structured front matter** in `_posts/YYYY-MM-DD-markets.md`,
like the AI cards. When `section: markets` **and** `format: markets-v2` are present,
`_includes/topic-body.html` renders `_includes/markets-report.html`. Posts without
`format: markets-v2` keep the old Markdown body (nothing breaks for old files).

The machine-checkable contract is **`docs/schemas/markets-post.schema.json`**
(JSON Schema 2020-12). `scripts/qa_markets.py` validates it and runs the content checks.
The auto-merge workflow only allows `_posts/`, `_data/*.csv` and `assets/issues/`, so all
issue data lives in the post file; the watchlist lives in `_data/watchlist.csv`.

## Daily flow

```
07:00  python3 scripts/fetch_markets.py --issue-date D --edition weekday|weekend \
           --out /workspace/newsletter/D/snapshot.json          # deterministic, no LLM
07:35  writer routine  -> /workspace/newsletter/D/markets-content.yml  (no dashboard numbers typed by hand)
08:00  reviewer routine edits markets-content.yml (style guide), then:
       python3 scripts/build_markets_post.py --content markets-content.yml --snapshot snapshot.json --out _posts/D-markets.md
       python3 scripts/qa_markets.py --fix _posts/D-markets.md   # drops failing items, logs them in `dropped`
08:25  publish routine opens the cursor/issue-* PR (auto-merge)
```

Never block the whole issue: failing claims or modules are dropped or shown as
**unavailable**, the rest publishes, and every drop is listed in `dropped` (rendered
at the bottom under "Data sources, licences and what was left out").

## Top-level keys

| Key | Type | Notes |
|---|---|---|
| `title`, `date` | string / datetime | Keep the date literal; it drives the permalink `/YYYY/MM/DD/markets/` |
| `section` | `markets` | |
| `edition` | `weekday` \| `weekend` | |
| `format` | `markets-v2` | Switches on the new template |
| `cutoff_local` | ISO datetime | Data cutoff in Sydney time (from the snapshot) |
| `session_note` | string | e.g. "Weekday ASX edition · before the 10:00 open" |
| `summary` | 3 strings | **If you read nothing else**. Markdown links allowed. Exactly 3. |
| `snapshot` | object | Written only by `fetch_markets.py` (see below) |
| `long_run_charts` | list | `brent` (FRED spot) and/or `gold` (COMEX futures) |
| `sections` | list | `id` ∈ `market-drivers`, `australia-asx`, `rates-expectations`, `global-risk`; each with `cards` |
| `rates` | object | `rba`, `fed` pricing blocks |
| `watchlist` | list | `{ticker, note, next_catalyst?, sources?}`; tickers come from `_data/watchlist.csv` |
| `calendar` | list | `{when, event, country?, importance?, actual?, prior?, consensus?, consensus_source?, source?}` |
| `dropped` | list | `{item, reason}`; QA appends here |

Section anchors are fixed on every edition: `#top-stories`, `#market-snapshot`,
`#market-drivers`, `#australia-asx`, `#rates-expectations`, `#global-risk`, `#watchlist`, `#calendar`.
There is no standalone analyst section (competing views live inside cards) and no
"More stories". Card budget: 8–12 across the four story sections, no filler (QA warns).

## `snapshot.quotes[]` (full provenance, filled by the script)

`id, display_name, tier (primary|expanded|watchlist), instrument_type, quote_kind
(spot|futures_last|futures_settle|index_close|close|yield|spread), unit, currency, decimals,
change_unit (pct|bp|pts), status (ok|unavailable), freshness_state
(live_or_delayed|latest_official_close|scheduled_lag|stale|unavailable), provider,
provider_url, licence_note, official, source_label ("official" | "delayed, unofficial"),
value, display_value, market_session_date, expected_session_date,
observation_timestamp_utc, observation_timezone, comparison_date, comparison_value,
change_abs|change_pct|change_bp, display_change, (weekend) week_* fields,
source_vintage, cross_checks[]`. Unavailable quotes carry `unavailable_reason`.

Conventions: yields and spreads move in **bp**; VIX in **index points**; prices/FX in %.
ASX futures are a separate instrument (currently unavailable) and never shown as the ASX 200.

## `cards[]`

| Field | Req | Notes |
|---|---|---|
| `id` | ✓ | kebab-case anchor, unique in the issue |
| `headline` | ✓ | factual, ideally ≤12 words |
| `takeaway` | ✓ | one objective line |
| `tags` | | ≤4 |
| `key_figure` | | only a verified figure, with unit and date |
| `new_since_last_issue` | | weekend/day-after delta |
| `what_happened`, `why_it_matters` | ✓ | Markdown; "why" may be conditional, never a prediction stated as fact |
| `market_reaction`, `priced_in`, `what_to_watch` | | Markdown |
| `competing_views` | | `{who, view, source}`; attributed opinions/forecasts/official claims |
| `sources` | ✓ | `{label, url, claim_type?, perspective?, date?}`; `claim_type` ∈ measurement, official_statement, reporting, forecast, opinion |
| `comparison` | | **Different figures** table, see below |
| `chart` | | `{type: bar|line, label, labels[], values[], unit, caption?, source, source_url?}` |

### `comparison` (conditional "Different figures" table)

Only when sources materially differ. Shows a `Different figures · N sources` pill on the
collapsed card and a table when expanded (stacked rows on phones).

```yaml
comparison:
  title: "Which Brent price?"
  why_different: "Different instruments and dates ..."
  resolution: explained        # explained | unresolved | reconciled
  rows:                        # at least 2
    - {source: "Yahoo Finance BZ=F", url: "https://...", figure: "US$109.86/bbl",
       measure: "Brent front-month futures, daily close", timestamp: "16 Oct 2026 session",
       method: "Exchange futures close", status: primary measured}
```
`status` ∈ primary measured, official claim, independently reported, unverified, estimate.
Never average or blend rows with different definitions.

## `rates`

```yaml
rates:
  rba:
    status: available          # or unavailable -> "Market pricing unavailable"
    summary: "About a one-in-eight chance of a hike in November."
    as_of: "16 Oct 2026"
    source: {label: Westpac Morning Report, url: "https://..."}
    forecasts: [{who: Westpac, view: "...", source: {label: ..., url: ...}}]
```
`available` requires a named, dated published source (bank or outlet). Never derive
probabilities ourselves from commentary.

## Calendar consensus

`consensus` is allowed only with `consensus_source` naming who published it; otherwise
show `actual` vs `prior` only.
