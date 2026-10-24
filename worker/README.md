# SignaLetter API (Cloudflare Worker)

Backs the "My shares" watchlist and (stub) email signup. The website stays on GitHub Pages;
this Worker only handles sign-in, each reader's share list, and signup confirmations.

## Endpoints
| Method | Path | What |
| --- | --- | --- |
| POST | `/auth/request` `{email, next}` | Emails a one-time sign-in link (15 min) to `SITE_ORIGIN/watchlist/?token=…` |
| POST | `/auth/verify` `{token}` | Exchanges the link token for a 30-day session token (bearer) |
| GET | `/me` | `{email, tickers, max}` for the signed-in reader |
| PUT | `/me/tickers` `{tickers:[…]}` | Saves up to `MAX_TICKERS` shares from `assets/data/asx-tickers.json` |
| DELETE | `/me` | Deletes the reader's data and signs out every device (all earlier sessions and unused links stop working) |
| POST | `/subscribe` `{email, lists:["markets","ai"]}` | Stub: double opt-in confirmation email |
| GET | `/subscribe/confirm?token=` / `GET,POST /unsubscribe?token=` | Stub confirm / unsubscribe |

Tokens are HMAC-SHA256 signed with `AUTH_SECRET`. CORS is limited to `ALLOWED_ORIGINS`.

Security state lives in a SQLite-backed Durable Object, `AuthState`, one per account (named by the
SHA-256 of the email), because Workers KV is eventually consistent and can't make these guarantees:
- **Single-use links:** `/auth/verify` redeems the link's nonce with one atomic `INSERT … ON CONFLICT DO
  NOTHING` inside the account's Durable Object, so concurrent verifies of one link give exactly one
  session. (KV `used:<nonce>` markers from before this change are still honoured until they expire.)
- **Revocation:** sessions and links carry the account's session version `v`; every authenticated
  request checks it against the Durable Object. `DELETE /me` bumps the version before deleting the
  KV data, so old sessions get 401 and can't recreate the account. Sessions issued before versioning
  have no `v`, count as version 0, and keep working until the account is deleted or they expire.

Rate limiting (5 sign-in emails per address per hour) uses KV and is best effort.
Reader data (`user:`, `sub:`) stays in KV; after a delete, another location may serve the old record
for up to ~60 s, but no session can read or write it.

## Local development
```bash
cd worker && npm install
cp .dev.vars.example .dev.vars          # no RESEND_API_KEY: links are logged and returned as dev_link
npm run dev                             # http://localhost:8787 (local KV in .wrangler/)
# second terminal, repo root:
bundle exec jekyll serve --config _config.yml,_config.local.yml --port 4000
npm run test:smoke                      # API smoke tests against localhost:8787
```

Regression tests (no server needed; run in workerd with local KV + Durable Objects, also run in CI):
```bash
cd worker && npm ci && npm test        # vitest + @cloudflare/vitest-plugin
npx wrangler deploy --dry-run           # bundle check (Wrangler needs Node 22+)
```

## Production setup checklist (all free tiers)
1. **Cloudflare account** (free) → Workers & Pages → choose a `workers.dev` subdomain.
2. `npx wrangler login`, then `npx wrangler kv namespace create WATCHLIST`; paste the id into `wrangler.toml`.
3. Secrets: `npx wrangler secret put AUTH_SECRET` (random, ≥32 chars, e.g. `openssl rand -base64 48`)
   and `npx wrangler secret put RESEND_API_KEY`.
4. **Resend account** (free) → Domains → add `signaletter.si` (or a subdomain such as `mail.signaletter.si`),
   copy the MX `send`, TXT `send` (SPF) and TXT `resend._domainkey` (DKIM) records into Hostinger DNS,
   then Verify. Create an API key with "Sending access" only for that domain.
5. Set `FROM_EMAIL` in `wrangler.toml` to an address on the verified domain; `npx wrangler deploy`.
6. In the site's `_config.yml`, set `watchlist_api: https://signaletter-api.<subdomain>.workers.dev`.
   Until this is set, the site renders exactly as before.
