import { cloudflareTest } from "@cloudflare/vitest-plugin";
import { defineConfig } from "vitest/config";

// Runs the Worker in workerd (Miniflare) with local KV + Durable Objects. No network, no real email.
export default defineConfig({
  plugins: [
    cloudflareTest({
      wrangler: { configPath: "./wrangler.toml" },
      miniflare: {
        bindings: {
          AUTH_SECRET: "test-secret-0123456789abcdef0123456789abcdef",
          ADMIN_TOKEN: "test-admin-token-0123456789abcdef0123456789",
          ALLOWED_ORIGINS: "http://localhost:4000",
          DEV_RETURN_LINK: "1",
        },
      },
    }),
  ],
  test: { include: ["test/**/*.spec.mjs"] },
});
