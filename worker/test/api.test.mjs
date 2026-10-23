// Smoke tests against a running `npm run dev` (wrangler dev with .dev.vars, no RESEND_API_KEY).
// Run: npm run dev  (one terminal), then: npm test
import test from "node:test";
import assert from "node:assert/strict";

const API = process.env.WL_API || "http://localhost:8787";
const ORIGIN = "http://localhost:4000";
const email = `t${Date.now()}@example.com`;
const call = async (method, path, body, token, origin = ORIGIN) => {
  const headers = { Origin: origin };
  if (body) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Bearer ${token}`;
  const r = await fetch(API + path, { method, headers, body: body ? JSON.stringify(body) : undefined });
  return { status: r.status, headers: r.headers, body: await r.json().catch(() => ({})) };
};

let session;
test("CORS only for allowed origins", async () => {
  const ok = await call("OPTIONS", "/me", null, null, ORIGIN);
  assert.equal(ok.headers.get("access-control-allow-origin"), ORIGIN);
  const bad = await fetch(API + "/me", { method: "OPTIONS", headers: { Origin: "https://evil.example" } });
  assert.equal(bad.headers.get("access-control-allow-origin"), null);
});
test("rejects bad email", async () => {
  assert.equal((await call("POST", "/auth/request", { email: "nope" })).status, 400);
});
test("magic link sign-in, single use, tamper-proof", async () => {
  const r = await call("POST", "/auth/request", { email, next: "/2026/10/22/markets/" });
  assert.equal(r.status, 200);
  const token = new URL(r.body.dev_link).searchParams.get("token");
  assert.equal((await call("POST", "/auth/verify", { token: token.slice(0, -2) + "xx" })).status, 401);
  const v = await call("POST", "/auth/verify", { token });
  assert.equal(v.status, 200);
  assert.equal(v.body.email, email);
  session = v.body.session;
  assert.equal((await call("POST", "/auth/verify", { token })).status, 401, "second use must fail");
});
test("tickers: validate, cap, dedupe, persist", async () => {
  assert.equal((await call("GET", "/me")).status, 401);
  assert.equal((await call("PUT", "/me/tickers", { tickers: ["BHP", "NOPE"] }, session)).status, 400);
  const eleven = ["BHP", "CBA", "NAB", "WBC", "ANZ", "MQG", "WES", "RIO", "FMG", "TLS", "WOW"];
  assert.equal((await call("PUT", "/me/tickers", { tickers: eleven }, session)).status, 400);
  const ok = await call("PUT", "/me/tickers", { tickers: ["bhp", "CBA.AX", "BHP"] }, session);
  assert.deepEqual(ok.body.tickers, ["BHP", "CBA"]);
  assert.deepEqual((await call("GET", "/me", null, session)).body.tickers, ["BHP", "CBA"]);
});
const ADMIN = process.env.WL_ADMIN_TOKEN || "test-admin-token-0123456789abcdef0123456789";
test("admin tickers: auth required, codes only, includes picks", async () => {
  assert.equal((await call("GET", "/admin/tickers")).status, 401);
  assert.equal((await call("GET", "/admin/tickers", null, "wrong-token-wrong-token-wrong-token-xx")).status, 401);
  assert.equal((await call("GET", "/admin/tickers", null, session)).status, 401, "reader session is not admin");
  const r = await call("GET", "/admin/tickers", null, ADMIN);
  assert.equal(r.status, 200);
  assert.ok(r.body.tickers.includes("BHP") && r.body.tickers.includes("CBA"));
  assert.equal(r.body.count, r.body.tickers.length);
  assert.ok(!JSON.stringify(r.body).includes("@"), "no emails");
});
test("instant add: picks missing from latest issue come back pending, deduped", async () => {
  // needs DEV_DISPATCH_MOCK=1 in .dev.vars; reads the live site's latest watchlist.json
  const r = await call("PUT", "/me/tickers", { tickers: ["BHP", "DRO"] }, session);
  assert.equal(r.status, 200);
  assert.ok(Array.isArray(r.body.pending));
  if (r.body.issue_date) {
    assert.ok(!r.body.pending.includes("BHP"), "BHP is a default, never pending");
    assert.ok(r.body.pending.includes("DRO"));
    const again = await call("PUT", "/me/tickers", { tickers: ["BHP", "DRO"] }, session);
    assert.deepEqual(again.body.pending, r.body.pending, "repeat save stays pending (deduped)");
  }
  await call("PUT", "/me/tickers", { tickers: ["BHP", "CBA"] }, session);
});
test("subscribe stub: double opt-in link", async () => {
  const r = await call("POST", "/subscribe", { email, lists: ["markets", "ai"] });
  assert.equal(r.status, 200);
  const confirm = await fetch(r.body.dev_link);
  assert.equal(confirm.status, 200);
  assert.match(await confirm.text(), /You're subscribed/);
});
test("delete my data", async () => {
  assert.equal((await call("DELETE", "/me", null, session)).status, 200);
  assert.deepEqual((await call("GET", "/me", null, session)).body.tickers, []);
  const r = await call("GET", "/admin/tickers", null, ADMIN);
  assert.ok(!r.body.tickers.includes("CBA") || r.body.readers >= 1);
});
