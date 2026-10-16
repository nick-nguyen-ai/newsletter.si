# newsletter.si

Daily ASX & global markets briefing — hosted on GitHub Pages at
[https://nick-nguyen-ai.github.io/newsletter.si/](https://nick-nguyen-ai.github.io/newsletter.si/).

Built with GitHub Pages’ native Jekyll. Push a markdown file to `main` and the
new issue publishes automatically. No manual build step.

## Add an issue

1. Create one file in `_posts/` named:

   ```
   YYYY-MM-DD-short-slug.md
   ```

   Examples:

   - `_posts/2026-10-17-asx-morning-briefing.md`
   - `_posts/2026-10-18-weekend-global-macro.md`

2. Start the file with this front matter (then the briefing body):

   ```yaml
   ---
   title: "ASX morning briefing: Friday 17 October"
   date: 2026-10-17
   edition: weekday
   ---
   ```

   | Field     | Required | Notes                                      |
   |-----------|----------|--------------------------------------------|
   | `title`   | yes      | Shown on the home page and issue page      |
   | `date`    | yes      | Prefer matching the filename date          |
   | `edition` | yes      | `weekday` or `weekend` (drives the badge)  |

3. Commit and push to `main`. GitHub Pages rebuilds the site.

That’s it — do not edit any other files.

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

## Feed

Atom feed: [/newsletter.si/feed.xml](https://nick-nguyen-ai.github.io/newsletter.si/feed.xml)

---

*Information only, not financial advice.*
