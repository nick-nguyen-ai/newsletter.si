# "My shares" (per-reader watchlist)

Only the watchlist section of a Markets page changes per reader. Everything else is the same static page.

- Signed out (or `watchlist_api` unset): the default list from `_data/watchlist.csv`, as before.
- Signed in: `assets/js/my-watchlist.js` reads the reader's tickers from the Worker (`worker/`) and rebuilds
  the Morning and Close watchlist sections from `assets/issues/<date>/watchlist.json`.
- Tickers a reader picked that are missing from that day's file show "Not in our data for this edition."
  Days with no file keep the default list and say so.

## Daily file: `assets/issues/YYYY-MM-DD/watchlist.json`
Built by `scripts/build_watchlist_json.py --date YYYY-MM-DD --tickers-file tickers.txt` after the Markets
post (and again after the close wrap). Schema `signaletter.watchlist/v1`:
`editions.{morning,close}.items.<TICKER> = {ticker, name, price{status, display_value, display_change,
session_date, provider, provider_url, …}, note, next_catalyst?, sources[], reviewed}`.

Facts only: prices reuse the post's own `wl_*` quotes when present, otherwise the Yahoo Finance daily close
vs the prior close (delayed, unofficial). Notes reuse the post's reviewed watchlist notes when present
(`reviewed: true`), otherwise list ASX announcement headlines in the edition window from the ASX
announcements feed (`reviewed: false`, labelled "auto: price + ASX feed" on the page). The feed only returns
the latest 5 items, so a busy ticker says "include:" or "not fully in our data" rather than "no announcement".

## Changes the daily routines would need (not made yet)
1. **Ticker set:** before building, fetch the union of all readers' tickers. Needs a small authenticated
   Worker endpoint (e.g. `GET /admin/tickers` with an `ADMIN_TOKEN` secret) or `wrangler kv key list`.
   Add the default four so the file always covers them.
2. **Morning publish (~08:25):** after `build_markets_post.py`, run
   `build_watchlist_json.py --date <today> --tickers-file <set>` and commit the JSON in the same `cursor/issue-*` PR.
3. **Close wrap (~16:15):** rerun the same command after `build_markets_post.py --close`, so the file gains
   the `close` edition, and commit it in the `cursor/issue-<date>-close` PR.
4. **QA:** extend the review step to check the file exists, every ticker in the set has a price or an explicit
   "unavailable", and auto notes contain no claims beyond price + announcement headlines.
5. **Universe refresh:** rerun `scripts/build_asx_list.py` after each quarterly S&P/ASX 200 rebalance.
