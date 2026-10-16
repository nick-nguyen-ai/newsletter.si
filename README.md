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

Then paste the briefing body using the structure below (unchanged from Hannah’s
usual format). The site turns it into a skimmable UI in the browser — **every
item is kept**; expand a card for the full summary, “For you:” line, and links.

### AI Markdown convention (keep writing like this)

```markdown
# Daily AI briefing for …

**The biggest story today:** …

## 1. Claude Code and Codex
**Item title**
Summary paragraph…
For you: …
[Source](https://…)

## 2. Other coding agents and dev tools
…same item pattern…

## 3. Evaluating and validating AI
## 4. Open-source agent frameworks
## 5. Big AI companies
## 6. General AI news to talk about

## 7. Trending on X
- [@handle …](https://x.com/…): one-liner

## 8. Trending AI papers
**Paper title:** …
(same item pattern as sections 1–6)

## 9. Trending AI repos on GitHub
1. [org/repo](https://github.com/…), description (N today).
```

Rules the skim UI relies on:

- One `**The biggest story today:**` line near the top
- Numbered `##` section headings (names can vary slightly; chips map by keyword)
- Story items: bold title on its own line, then summary + optional `For you:` + links (blank line before the next title)
- Mark uncertain items with `(unconfirmed)` in the title or body
- Section 7 = bullet list; section 8 = paper items; section 9 = numbered repo list

**AI coding agents (render-time merge):** headings like “Claude Code and Codex” and
“Other coding agents and dev tools” are merged into one section titled **AI coding
agents**, with a single filter chip. All items from both headings are kept. Each
card gets small per-agent tags detected from the item text (Claude Code, Codex,
Cursor, Copilot, Gemini CLI, Pi, OpenCode, Grok, Aider, Cline, and similar). You
can keep writing the two old headings — no Markdown change required.

The rendered page shows: **Today in 30 seconds** (biggest story + top 5 one-liners),
section filter chips, expandable cards (with agent tags in the coding-agents
section), and dense tables for papers/repos.

### Publish

Commit and push to `main`. That’s it — do not edit any other files.

Same-day Markets + AI appear on one issue page (Markets first, then AI), with an
anchor switcher. The archive shows **one row per day**, with badges for which
sections exist.

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

Series run from **2020-01-01** (no invented values; blank closes where the source has gaps).

| Series | Path | Columns | Source |
|--------|------|---------|--------|
| Brent crude (USD/bbl) | `_data/brent.csv` | `date,close` | [FRED DCOILBRENTEU](https://fred.stlouisfed.org/series/DCOILBRENTEU) |
| Gold (USD/oz) | `_data/gold.csv` | `date,close` | [Yahoo Finance GC=F](https://finance.yahoo.com/quote/GC=F/) (COMEX); LBMA daily was removed from FRED |

Metadata (labels, units, sources, era markers/bands) is in `_data/charts.yml`.

Charts default to **2020–now**, with quick ranges **1M / 6M / 1Y / Since war / 2020–now**. Long ranges downsample to weekly for mobile performance. Each chart header shows the latest print and change vs a year ago. Era overlays: COVID (Mar 2020), Ukraine (24 Feb 2022), Biden band, Trump 2nd-term band, US–Iran war (28 Feb 2026). All issues share the same CSV files (intended — the line is always current).

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
