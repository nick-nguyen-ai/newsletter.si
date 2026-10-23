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
| DELETE | `/me` | Deletes the reader's data |
| POST | `/subscribe` `{email, lists:["markets","ai"]}` | Stub: double opt-in confirmation email |
| GET | `/subscribe/confirm?token=` / `GET,POST /unsubscribe?token=` | Stub confirm / unsubscribe |

Tokens are HMAC-SHA256 signed with `AUTH_SECRET`. Sign-in links are single-use (best effort, via KV)
and rate-limited to 5 emails per address per hour. CORS is limited to `ALLOWED_ORIGINS`.

## Local development
```bash
cd worker && npm install
cp .dev.vars.example .dev.vars          # no RESEND_API_KEY: links are logged and returned as dev_link
npm run dev                             # http://localhost:8787 (local KV in .wrangler/)
# second terminal, repo root:
bundle exec jekyll serve --config _config.yml,_config.local.yml --port 4000
npm test                                # API smoke tests against localhost:8787
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
