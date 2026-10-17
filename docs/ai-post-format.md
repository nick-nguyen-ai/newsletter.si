# AI post front-matter format

Daily AI issues can ship as **structured cards** in the post’s YAML front matter.
The auto-merge workflow only allows `_posts/`, `_data/*.csv`, and `assets/issues/`,
so all card data must live in the post file itself.

When `signal` and `sections` are present (and `section: ai`), the site renders the
card UI (Today’s AI Signal, section nav, expandable cards). Posts without those
keys keep the older Markdown body + skim UI.

## Required keys

Keep the usual post keys, then add `signal` and `sections`:

| Key | Type | Notes |
|-----|------|--------|
| `title` | string | Page / SEO title |
| `date` | datetime | Prefer timezone-safe, e.g. `2026-10-18 08:25:00 +1100` |
| `section` | `ai` | Required |
| `signal` | list | Up to ~3 lead stories |
| `sections` | list | Ordered sections with nested `cards` |

### `signal[]`

| Field | Type | Notes |
|-------|------|--------|
| `section_id` | string | Must match a `sections[].id` |
| `card_id` | string | Must match a card `id` in that section |
| `headline` | string | Shown in the Signal list (can differ slightly from the card headline) |

### `sections[]`

| Field | Type | Notes |
|-------|------|--------|
| `id` | string | Stable id (`coding`, `evals`, …) |
| `name` | string | Display name |
| `cards` | list | Items in this section |

### `cards[]`

| Field | Type | Notes |
|-------|------|--------|
| `id` | string | Anchor id (unique in the issue) |
| `headline` | string | Card title |
| `takeaway` | string | One-line summary |
| `tags` | string list | Topic chips |
| `sources` | string list | Source chips (Blog, X, …) |
| `verdict` | string | Exactly `Worth trying`, `Worth reading`, or `Monitor only` |
| `what_changed` | string | Expanded detail |
| `why_it_matters` | string | Expanded detail |
| `caveats` | string | Optional; use `""` if none |
| `how_to_try` | string | Optional (coding agents); omit or `""` if N/A |
| `links` | list | `{ label, url }` objects |

## Minimal example

```yaml
---
title: "Daily AI report · Friday 18 Oct 2026"
date: 2026-10-18 08:25:00 +1100
section: ai
signal:
  - section_id: coding
    card_id: example-card
    headline: Example lead story
sections:
  - id: coding
    name: Coding Agents
    cards:
      - id: example-card
        headline: Example lead story
        takeaway: One sentence readers can skim.
        tags:
          - Claude Code
        sources:
          - Changelog
        verdict: Worth trying
        what_changed: What shipped or changed.
        why_it_matters: Why it matters for validation work.
        caveats: ""
        how_to_try: One concrete next step.
        links:
          - label: Release notes
            url: https://example.com
---
```

Leave the Markdown body empty when using cards. Escape quotes in YAML as usual
(`'` inside single-quoted strings becomes `''`).
