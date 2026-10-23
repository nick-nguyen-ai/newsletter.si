// SignaLetter API: passwordless sign-in, per-reader "My shares" watchlist, email signup stub.
// Storage: one Workers KV namespace (binding WATCHLIST).
//   user:<email>        -> {"tickers":[...],"created":iso,"updated":iso}
//   used:<nonce>        -> "1" (TTL 20 min; makes magic links single-use, best effort)
//   rl:<email>:<hour>   -> count (TTL 1h; sign-in email rate limit)
//   sub:<email>         -> {"lists":[...],"status":"pending"|"confirmed","updated":iso}
// Tokens are HMAC-SHA256 signed with AUTH_SECRET, so verifying them never depends on KV
// propagation between Cloudflare locations.
import asx from "../../assets/data/asx-tickers.json";

const ALLOWED = new Map(asx.tickers.map((t) => [t.code, t.name]));
const LOGIN_TTL = 15 * 60; // magic link: 15 minutes
const SESSION_TTL = 30 * 24 * 3600; // session: 30 days
const CONFIRM_TTL = 3 * 24 * 3600; // subscribe confirmation: 3 days
const SIGNIN_PER_HOUR = 5;
const LISTS = ["markets", "ai"];
const enc = new TextEncoder();

// ---------- helpers ----------
const b64u = (buf) =>
  btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
const b64uText = (s) => b64u(enc.encode(s));
const unb64uText = (s) => {
  const bin = atob(s.replace(/-/g, "+").replace(/_/g, "/"));
  return new TextDecoder().decode(Uint8Array.from(bin, (c) => c.charCodeAt(0)));
};
const now = () => Math.floor(Date.now() / 1000);
const nonce = () => b64u(crypto.getRandomValues(new Uint8Array(16)));

async function hmacKey(secret) {
  return crypto.subtle.importKey("raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, [
    "sign",
    "verify",
  ]);
}
async function sign(env, payload) {
  const body = b64uText(JSON.stringify(payload));
  const sig = await crypto.subtle.sign("HMAC", await hmacKey(env.AUTH_SECRET), enc.encode(body));
  return `${body}.${b64u(sig)}`;
}
async function verify(env, token, purpose) {
  if (typeof token !== "string" || token.length > 2048) return null;
  const [body, sig] = token.split(".");
  if (!body || !sig) return null;
  let sigBytes;
  try {
    sigBytes = Uint8Array.from(atob(sig.replace(/-/g, "+").replace(/_/g, "/")), (c) => c.charCodeAt(0));
  } catch {
    return null;
  }
  const ok = await crypto.subtle.verify("HMAC", await hmacKey(env.AUTH_SECRET), sigBytes, enc.encode(body));
  if (!ok) return null;
  let p;
  try {
    p = JSON.parse(unb64uText(body));
  } catch {
    return null;
  }
  if (p.p !== purpose || typeof p.exp !== "number" || p.exp < now()) return null;
  return p;
}

const EMAIL_RE = /^[^\s@<>()",;:]{1,64}@[A-Za-z0-9.-]{1,253}\.[A-Za-z]{2,}$/;
const normEmail = (e) => (typeof e === "string" ? e.trim().toLowerCase() : "");
const validEmail = (e) => e.length <= 254 && EMAIL_RE.test(e);
const safeNext = (n) => (typeof n === "string" && /^\/(?!\/)[\w\-./#%?=&]*$/.test(n) && n.length < 300 ? n : "");
const escapeHtml = (s) =>
  String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

function corsHeaders(env, req) {
  const origin = req.headers.get("Origin") || "";
  const allowed = (env.ALLOWED_ORIGINS || "").split(",").map((s) => s.trim()).filter(Boolean);
  const h = { Vary: "Origin" };
  if (allowed.includes(origin)) {
    h["Access-Control-Allow-Origin"] = origin;
    h["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS";
    h["Access-Control-Allow-Headers"] = "Authorization,Content-Type";
    h["Access-Control-Max-Age"] = "600";
  }
  return h;
}
const json = (env, req, data, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store", ...corsHeaders(env, req) },
  });
const html = (body, status = 200) =>
  new Response(
    `<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SignaLetter</title><body style="font-family:system-ui,sans-serif;max-width:32rem;margin:3rem auto;padding:0 1rem;line-height:1.5">${body}</body>`,
    { status, headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" } },
  );

async function readJson(req) {
  if (!(req.headers.get("Content-Type") || "").includes("application/json")) return null;
  try {
    const t = await req.text();
    return t.length > 4096 ? null : JSON.parse(t);
  } catch {
    return null;
  }
}

async function sendEmail(env, { to, subject, text, htmlBody }) {
  if (!env.RESEND_API_KEY) {
    console.log(`[mock email] to=${to} subject=${JSON.stringify(subject)}\n${text}`);
    return { mocked: true };
  }
  const r = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { Authorization: `Bearer ${env.RESEND_API_KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({ from: env.FROM_EMAIL, to: [to], subject, text, html: htmlBody }),
  });
  if (!r.ok) {
    console.log(`resend error ${r.status}: ${await r.text()}`);
    throw new Error("email_failed");
  }
  return { mocked: false };
}

async function session(env, req) {
  const m = (req.headers.get("Authorization") || "").match(/^Bearer (.+)$/);
  if (!m) return null;
  return verify(env, m[1], "session");
}

function cleanTickers(list, max) {
  if (!Array.isArray(list)) return { error: "tickers must be a list" };
  const out = [];
  for (const raw of list) {
    const t = String(raw || "").trim().toUpperCase().replace(/\.AX$/, "");
    if (!t) continue;
    if (!ALLOWED.has(t)) return { error: `${t} is not in the supported ASX list` };
    if (!out.includes(t)) out.push(t);
  }
  if (out.length > max) return { error: `Pick up to ${max} shares` };
  return { tickers: out };
}

// ---------- routes ----------
async function authRequest(env, req) {
  const body = await readJson(req);
  const email = normEmail(body && body.email);
  if (!validEmail(email)) return json(env, req, { ok: false, error: "Enter a valid email address." }, 400);
  const next = safeNext(body.next);
  const hour = Math.floor(now() / 3600);
  const rlKey = `rl:${email}:${hour}`;
  const count = parseInt((await env.WATCHLIST.get(rlKey)) || "0", 10);
  if (count >= SIGNIN_PER_HOUR)
    return json(env, req, { ok: false, error: "Too many sign-in emails. Try again in an hour." }, 429);
  await env.WATCHLIST.put(rlKey, String(count + 1), { expirationTtl: 3600 });

  const token = await sign(env, { p: "login", e: email, exp: now() + LOGIN_TTL, n: nonce() });
  const url = new URL("/watchlist/", env.SITE_ORIGIN);
  url.searchParams.set("token", token);
  if (next) url.searchParams.set("next", next);
  const link = url.toString();
  const text = `Sign in to SignaLetter to track your own shares:\n\n${link}\n\nThis link works once and expires in 15 minutes. If you didn't ask for it, ignore this email.\n\nSignaLetter · https://signaletter.si`;
  const htmlBody = `<p>Sign in to SignaLetter to track your own shares:</p><p><a href="${escapeHtml(link)}">Sign in to SignaLetter</a></p><p>This link works once and expires in 15 minutes. If you didn't ask for it, ignore this email.</p><p>SignaLetter · <a href="https://signaletter.si">signaletter.si</a></p>`;
  let mocked;
  try {
    ({ mocked } = await sendEmail(env, { to: email, subject: "Your SignaLetter sign-in link", text, htmlBody }));
  } catch {
    return json(env, req, { ok: false, error: "We couldn't send the email. Try again shortly." }, 502);
  }
  const res = { ok: true };
  if (mocked && env.DEV_RETURN_LINK === "1") res.dev_link = link;
  return json(env, req, res);
}

async function authVerify(env, req) {
  const body = await readJson(req);
  const p = await verify(env, body && body.token, "login");
  if (!p) return json(env, req, { ok: false, error: "This sign-in link is invalid or has expired." }, 401);
  const usedKey = `used:${p.n}`;
  if (await env.WATCHLIST.get(usedKey))
    return json(env, req, { ok: false, error: "This sign-in link has already been used." }, 401);
  await env.WATCHLIST.put(usedKey, "1", { expirationTtl: LOGIN_TTL + 300 });
  const userKey = `user:${p.e}`;
  if (!(await env.WATCHLIST.get(userKey))) {
    const t = new Date().toISOString();
    await env.WATCHLIST.put(userKey, JSON.stringify({ tickers: [], created: t, updated: t }));
  }
  const s = await sign(env, { p: "session", e: p.e, exp: now() + SESSION_TTL });
  return json(env, req, { ok: true, session: s, email: p.e, expires_in: SESSION_TTL });
}

async function getMe(env, req) {
  const s = await session(env, req);
  if (!s) return json(env, req, { ok: false, error: "signed_out" }, 401);
  const u = JSON.parse((await env.WATCHLIST.get(`user:${s.e}`)) || '{"tickers":[]}');
  return json(env, req, { ok: true, email: s.e, tickers: u.tickers || [], max: parseInt(env.MAX_TICKERS || "10", 10) });
}

async function putTickers(env, req) {
  const s = await session(env, req);
  if (!s) return json(env, req, { ok: false, error: "signed_out" }, 401);
  const body = await readJson(req);
  const r = cleanTickers(body && body.tickers, parseInt(env.MAX_TICKERS || "10", 10));
  if (r.error) return json(env, req, { ok: false, error: r.error }, 400);
  const key = `user:${s.e}`;
  const u = JSON.parse((await env.WATCHLIST.get(key)) || "{}");
  const t = new Date().toISOString();
  // Tickers are mirrored into key metadata so GET /admin/tickers can build the union from one KV list call.
  await env.WATCHLIST.put(key, JSON.stringify({ created: u.created || t, ...u, tickers: r.tickers, updated: t }), {
    metadata: { t: r.tickers },
  });
  return json(env, req, { ok: true, tickers: r.tickers });
}

async function deleteMe(env, req) {
  const s = await session(env, req);
  if (!s) return json(env, req, { ok: false, error: "signed_out" }, 401);
  await env.WATCHLIST.delete(`user:${s.e}`);
  await env.WATCHLIST.delete(`sub:${s.e}`);
  return json(env, req, { ok: true });
}

// Union of every reader's tickers, for the daily watchlist.json build. Codes only, never emails.
async function timingSafeEqual(a, b) {
  const k = await crypto.subtle.importKey("raw", crypto.getRandomValues(new Uint8Array(32)), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const [x, y] = await Promise.all([crypto.subtle.sign("HMAC", k, enc.encode(a)), crypto.subtle.sign("HMAC", k, enc.encode(b))]);
  const ua = new Uint8Array(x), ub = new Uint8Array(y);
  let d = 0;
  for (let i = 0; i < ua.length; i++) d |= ua[i] ^ ub[i];
  return d === 0;
}
async function adminTickers(env, req) {
  const m = (req.headers.get("Authorization") || "").match(/^Bearer (.+)$/);
  if (!env.ADMIN_TOKEN || env.ADMIN_TOKEN.length < 32 || !m || !(await timingSafeEqual(m[1], env.ADMIN_TOKEN)))
    return json(env, req, { ok: false, error: "unauthorized" }, 401);
  const set = new Set();
  let cursor, readers = 0;
  do {
    const page = await env.WATCHLIST.list({ prefix: "user:", cursor });
    for (const k of page.keys) {
      let t = k.metadata && Array.isArray(k.metadata.t) ? k.metadata.t : null;
      if (!t) t = (JSON.parse((await env.WATCHLIST.get(k.name)) || "{}").tickers) || []; // pre-metadata records
      if (t.length) readers++;
      for (const x of t) if (ALLOWED.has(x)) set.add(x);
    }
    cursor = page.list_complete ? undefined : page.cursor;
  } while (cursor);
  const tickers = [...set].sort();
  return json(env, req, { ok: true, tickers, count: tickers.length, readers });
}

// Email-only subscription (stub): double opt-in, stored in KV. Sending the daily notice
// (e.g. via Resend Broadcasts/contacts) is not wired up yet.
async function subscribe(env, req) {
  const body = await readJson(req);
  const email = normEmail(body && body.email);
  if (!validEmail(email)) return json(env, req, { ok: false, error: "Enter a valid email address." }, 400);
  const lists = Array.isArray(body.lists) ? body.lists.filter((l) => LISTS.includes(l)) : [];
  if (!lists.length) return json(env, req, { ok: false, error: "Choose Markets, AI or both." }, 400);
  const hour = Math.floor(now() / 3600);
  const rlKey = `rl:${email}:${hour}`;
  const count = parseInt((await env.WATCHLIST.get(rlKey)) || "0", 10);
  if (count >= SIGNIN_PER_HOUR) return json(env, req, { ok: false, error: "Too many requests. Try later." }, 429);
  await env.WATCHLIST.put(rlKey, String(count + 1), { expirationTtl: 3600 });
  const prev = JSON.parse((await env.WATCHLIST.get(`sub:${email}`)) || "null");
  if (!prev || prev.status !== "confirmed")
    await env.WATCHLIST.put(`sub:${email}`, JSON.stringify({ lists, status: "pending", updated: new Date().toISOString() }));
  const token = await sign(env, { p: "confirm", e: email, l: lists, exp: now() + CONFIRM_TTL });
  const link = `${new URL(req.url).origin}/subscribe/confirm?token=${encodeURIComponent(token)}`;
  const names = lists.map((l) => (l === "ai" ? "AI" : "Markets")).join(" and ");
  const text = `Confirm your SignaLetter subscription (${names}):\n\n${link}\n\nIf you didn't sign up, ignore this email and you won't hear from us.\n\nSignaLetter · https://signaletter.si`;
  let mocked;
  try {
    ({ mocked } = await sendEmail(env, {
      to: email,
      subject: "Confirm your SignaLetter subscription",
      text,
      htmlBody: `<p>Confirm your SignaLetter subscription (${escapeHtml(names)}):</p><p><a href="${escapeHtml(link)}">Confirm subscription</a></p><p>If you didn't sign up, ignore this email.</p>`,
    }));
  } catch {
    return json(env, req, { ok: false, error: "We couldn't send the email. Try again shortly." }, 502);
  }
  const res = { ok: true };
  if (mocked && env.DEV_RETURN_LINK === "1") res.dev_link = link;
  return json(env, req, res);
}

async function confirmSub(env, url) {
  const p = await verify(env, url.searchParams.get("token"), "confirm");
  if (!p) return html("<h1>Link expired</h1><p>Please sign up again on <a href='https://signaletter.si'>SignaLetter</a>.</p>", 400);
  await env.WATCHLIST.put(`sub:${p.e}`, JSON.stringify({ lists: p.l, status: "confirmed", updated: new Date().toISOString() }));
  const unsub = await sign(env, { p: "unsub", e: p.e, exp: now() + 10 * 365 * 24 * 3600 });
  return html(
    `<h1>You're subscribed</h1><p>${escapeHtml(p.e)} will get the SignaLetter ${p.l.map((l) => (l === "ai" ? "AI" : "Markets")).join(" and ")} email.</p><p><a href="${escapeHtml(env.SITE_ORIGIN)}">Back to SignaLetter</a> · <a href="/unsubscribe?token=${encodeURIComponent(unsub)}">Unsubscribe</a></p>`,
  );
}

async function unsubscribe(env, req, url) {
  const p = await verify(env, url.searchParams.get("token"), "unsub");
  if (!p) return html("<h1>Invalid link</h1>", 400);
  // GET shows a confirm button (mail scanners prefetch links); POST is RFC 8058 one-click.
  if (req.method === "GET")
    return html(
      `<h1>Unsubscribe?</h1><form method="post"><button type="submit">Unsubscribe ${escapeHtml(p.e)}</button></form>`,
    );
  await env.WATCHLIST.delete(`sub:${p.e}`);
  return html("<h1>Unsubscribed</h1><p>You won't get SignaLetter emails any more.</p>");
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    if (!env.AUTH_SECRET || env.AUTH_SECRET.length < 32)
      return json(env, req, { ok: false, error: "server_not_configured" }, 500);
    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: corsHeaders(env, req) });
    const route = `${req.method} ${url.pathname}`;
    try {
      switch (route) {
        case "GET /":
        case "GET /health":
          return json(env, req, { ok: true, service: "signaletter-api", tickers: ALLOWED.size });
        case "POST /auth/request":
          return await authRequest(env, req);
        case "POST /auth/verify":
          return await authVerify(env, req);
        case "GET /me":
          return await getMe(env, req);
        case "PUT /me/tickers":
          return await putTickers(env, req);
        case "DELETE /me":
          return await deleteMe(env, req);
        case "GET /admin/tickers":
          return await adminTickers(env, req);
        case "POST /subscribe":
          return await subscribe(env, req);
        case "GET /subscribe/confirm":
          return await confirmSub(env, url);
        case "GET /unsubscribe":
        case "POST /unsubscribe":
          return await unsubscribe(env, req, url);
        default:
          return json(env, req, { ok: false, error: "not_found" }, 404);
      }
    } catch (e) {
      console.log(`error ${route}: ${e && e.stack}`);
      return json(env, req, { ok: false, error: "server_error" }, 500);
    }
  },
};
