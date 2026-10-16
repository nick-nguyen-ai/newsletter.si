# newsletter.si

Daily ASX & global markets briefing, plus a daily AI report — hosted on GitHub Pages at
[https://nick-nguyen-ai.github.io/newsletter.si/](https://nick-nguyen-ai.github.io/newsletter.si/).

Two streams share one calendar day:

1. **Markets** — weekday ASX morning briefing, or weekend global macro
2. **AI** — daily AI report (long-form, sectioned)

Built with GitHub Pages’ native Jekyll. Push a markdown file to `main` and it
publishes automatically. No manual build step.

## Add an issue (one file per section)

Create **one markdown file per section** in `_posts/`. You can add Markets only,
AI only, or both for the same date — each is a separate file.

### File naming

```
_posts/YYYY-MM-DD-markets.md
_posts/YYYY-MM-DD-ai.md
```

The slug after the date becomes the URL segment (`…/markets/`, `…/ai/`), so use
`markets` and `ai` there. The `section` front-matter field must still be set
(`markets` or `ai`) — that is what groups the day and drives the badges.
Prefer matching the filename date to the `date` field.

### Markets front matter

```yaml
---
title: "ASX morning briefing: Friday 17 October"
date: 2026-10-17
section: markets
edition: weekday
---
```

| Field     | Required | Notes                                     |
|-----------|----------|-------------------------------------------|
| `title`   | yes      | Section title on the day page             |
| `date`    | yes      | Calendar day (group key)                  |
| `section` | yes      | Must be `markets`                         |
| `edition` | yes      | `weekday` or `weekend` (badge)            |

### AI front matter

```yaml
---
title: "Daily AI briefing for Friday 17 Oct 2026"
date: 2026-10-17
section: ai
---
```

| Field     | Required | Notes                          |
|-----------|----------|--------------------------------|
| `title`   | yes      | Section title on the day page  |
| `date`    | yes      | Calendar day (group key)       |
| `section` | yes      | Must be `ai`                   |

Then paste the briefing body. For AI, keep the usual `#` title, biggest-story
line, and `##` numbered sections — the site builds a table of contents from those
headings. Text like `(unconfirmed)` or `**Unconfirmed**` is styled as a muted badge.

### Publish

Commit and push to `main`. That’s it — do not edit any other files.

Same-day Markets + AI appear on one issue page (Markets first, then AI), with an
anchor switcher and an AI table of contents. The archive shows **one row per day**,
with badges for which sections exist.

## Enable GitHub Pages

One-time setup in the repo:

1. **Settings → Pages**
2. Under **Build and deployment**, set **Source** to **Deploy from a branch**
3. Branch: **main**, folder: **/ (root)**
4. Save

The site will be at `https://nick-nguyen-ai.github.io/newsletter.si/`.

## Local preview (optional)

```bash
bundle install
bundle exec jekyll serve
```

Open http://127.0.0.1:4000/newsletter.si/

## Charts (oil & gold)

Persistent daily time series live in `_data/`. Charts use Chart.js 4.4.6 from a
pinned jsDelivr CDN URL with SRI (no npm build step).

### War start marker

**28 February 2026** — US–Iran war begins (US–Israeli airstrikes; Strait of Hormuz
crisis the same day). Cited from [AP News](https://apnews.com/article/iran-us-timeline-trump-hormuz-war-ceasefire-04da58cbae991183f8b52ef5bf615963),
[ABC News](https://abcnews.com/International/iran-war-timeline-1-month-escalating-strikes-broadening/story?id=131606351),
and [CNN](https://www.cnn.com/interactive/2026/05/politics/iran-war-key-moments-vis/).
Series files start on that date; the charts draw a vertical marker there. No
invented or interpolated prices — missing source days are left blank.

### Data files

| Series | Path | Columns | Source |
|--------|------|---------|--------|
| Brent crude (USD/bbl) | `_data/brent.csv` | `date,close` | [FRED DCOILBRENTEU](https://fred.stlouisfed.org/series/DCOILBRENTEU) |
| Gold (USD/oz) | `_data/gold.csv` | `date,close` | [Yahoo Finance GC=F](https://finance.yahoo.com/quote/GC=F/) (COMEX); LBMA daily was removed from FRED |

Metadata (labels, units, sources, war marker) is in `_data/charts.yml`.

### Append one row (daily process)

After each session close, append **one line** to each file (no header change):

```text
_data/brent.csv
2026-10-17,127.40

_data/gold.csv
2026-10-17,4210.50
```

Format: `YYYY-MM-DD,close` with the close as a plain number (no `$`, no thousands
separator). If the source has no print that day, either skip the row or append
`YYYY-MM-DD,` with an empty close (the chart leaves a gap).

### Embed a chart in a post

Known series (war marker included):

```liquid
{% include chart.html series="brent" %}
{% include chart.html series="gold" caption="Gold since the war began (USD/oz)." %}
```

One-off bar/line chart from inline data:

```liquid
{% include chart-data.html
     type="bar"
     label="ASX sectors"
     labels='["Banks","Miners","Tech"]'
     values='[1.2,-0.4,0.3]'
     unit="%"
     caption="One-day sector moves." %}
```

Or from any `_data/*.csv`:

```liquid
{% include chart-data.html data="brent" type="line" label="Brent" x="date" y="close" %}
```

## Feed

Atom feed: [/newsletter.si/feed.xml](https://nick-nguyen-ai.github.io/newsletter.si/feed.xml)
(one entry per section file).

---

*Information only, not financial advice.*
