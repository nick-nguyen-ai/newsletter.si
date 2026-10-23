# "My shares" (per-reader watchlist)

Only the watchlist section of a Markets page changes per reader. Everything else is the same static page.

- Signed out (or `watchlist_api` unset): the default list from `_data/watchlist.csv`, as before.
- Signed in: `assets/js/my-watchlist.js` reads the reader's tickers from the Worker (`worker/`) and rebuilds
  the Morning and Close watchlist sections from `assets/issues/<date>/watchlist.json`.
- Tickers a reader picked that are missing from that day's file show "Not in our data for this edition."
  Days with no file keep the default list and say so.

## Daily file: `assets/issues/YYYY-MM-DD/watchlist.json`
Built by `scripts/build_watchlist_json.py --date YYYY-MM-DD` after the Markets post (and again after the
close wrap). Schema `signaletter.watchlist/v1`:
`editions.{morning,close}.items.<TICKER> = {ticker, name, price{status, display_value, display_change,
session_date, provider, provider_url, …}, note, next_catalyst?, sources[], reviewed}`.

Facts only: prices reuse the post's own `wl_*` quotes when present, otherwise the Yahoo Finance daily close
vs the prior close (delayed, unofficial). Notes reuse the post's reviewed watchlist notes when present
(`reviewed: true`), otherwise list ASX announcement headlines in the edition window from the ASX
announcements feed (`reviewed: false`, labelled "auto: price + ASX feed" on the page). The feed only returns
the latest 5 items, so a busy ticker says "include:" or "not fully in our data" rather than "no announcement".

## Daily step (Morning and Close routines)
Ticker set = the 30 defaults in `assets/data/watchlist-default-tickers.txt` + every reader's picks, fetched
from the Worker's `GET /admin/tickers` (codes only, never emails; bearer `ADMIN_TOKEN`, read from
`$SIGNALETTER_ADMIN_TOKEN` or `~/.config/signaletter/admin_token`, chmod 600).

1. **Morning (~08:25):** after `build_markets_post.py` writes the post, run from the repo root
   `python3 scripts/build_watchlist_json.py --date <YYYY-MM-DD>` and commit
   `assets/issues/<date>/watchlist.json` in the same `cursor/issue-*` PR.
2. **Close (~16:15):** after `build_markets_post.py --close`, rerun the same command (the file gains the
   `close` edition) and commit it in the `cursor/issue-<date>-close` PR.
3. Check the last output line: `reader picks N; added beyond defaults: [...]`. `reader picks unavailable`
   means the token or Worker failed; the file then covers only the defaults, so fix and rerun.

A reader who picks a share mid-day sees it from the next Morning or Close run. Picks outside the allowed list
are skipped with a warning.

## Ticker universe
`assets/data/asx-tickers.json` = S&P/ASX 300 constituents from Vanguard VAS holdings (VAS fully replicates the
index; holdings updated monthly), filtered to ASX's listed-companies file, plus the default watchlist. Rerun
`python3 scripts/build_asx_list.py` monthly or after each S&P rebalance (March/September), then redeploy the
Worker (`cd worker && npx wrangler deploy`), since it bundles the list for validation.

## Still to do
- QA step: check the file exists and every ticker has a price or an explicit "unavailable".
