import { defineConfig } from "@playwright/test";

// Behavioral-proof config for the real verifier layer. In the sandbox the
// trivial-slice proof is captured via `next build` + `next start` + curl
// (see tools/prove_trivial_slice.py); this config wires the full Playwright
// run for when browser binaries are available (Vercel preview / CI).
export default defineConfig({
  testDir: "./tests/e2e",
  use: { trace: "on", baseURL: "http://localhost:3000" },
  webServer: {
    command: "npm run build && npm run start",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
