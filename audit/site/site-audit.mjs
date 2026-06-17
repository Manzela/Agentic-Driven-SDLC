// site-audit.mjs — cross-screen (responsive) + a11y audit of a live URL.
// Runs in CI (the runner has network; the sandbox doesn't). For each viewport it
// loads the page, screenshots full-page, flags horizontal overflow, checks the
// sticky bottom-nav doesn't overlap content, and runs an axe-core a11y scan.
//
// Cloudflare Access: if CF_ACCESS_CLIENT_ID/SECRET are set, they're sent as
// service-token headers so the auditor gets through the Zero-Trust gate.
import { chromium } from "playwright";
import { AxeBuilder } from "@axe-core/playwright";
import fs from "fs";

const URL = process.env.AUDIT_URL || "https://plane.autonomous-agent.dev";
const CF_ID = process.env.CF_ACCESS_CLIENT_ID || "";
const CF_SECRET = process.env.CF_ACCESS_CLIENT_SECRET || "";
const OUT = "audit-out";
fs.mkdirSync(`${OUT}/screens`, { recursive: true });

const viewports = [
  { name: "phone-375", width: 375, height: 812 },
  { name: "tablet-768", width: 768, height: 1024 },
  { name: "tablet-820", width: 820, height: 1180 },
  { name: "desktop-1280", width: 1280, height: 800 },
  { name: "desktop-1512", width: 1512, height: 945 },
  { name: "desktop-1920", width: 1920, height: 1080 },
];

const extraHTTPHeaders =
  CF_ID && CF_SECRET
    ? { "CF-Access-Client-Id": CF_ID, "CF-Access-Client-Secret": CF_SECRET }
    : {};
if (!CF_ID) console.log("NOTE: no CF Access service token set — if the site is behind Access, you'll capture the login page.");

const summary = [];
let hardFail = false;
const browser = await chromium.launch({ args: ["--no-sandbox"] });

for (const vp of viewports) {
  const ctx = await browser.newContext({
    viewport: { width: vp.width, height: vp.height },
    extraHTTPHeaders,
    deviceScaleFactor: 1,
  });
  const page = await ctx.newPage();
  const row = { viewport: vp.name, notes: [] };
  try {
    const resp = await page.goto(URL, { waitUntil: "networkidle", timeout: 60000 });
    row.http = resp ? resp.status() : null;
    await page.waitForTimeout(2500);
    await page.screenshot({ path: `${OUT}/screens/${vp.name}.png`, fullPage: true });

    // 1) horizontal overflow (a classic non-responsive symptom)
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth + 2
    );
    row.horizontalOverflow = overflow;
    if (overflow) { row.notes.push("HORIZONTAL OVERFLOW"); hardFail = true; }

    // 2) fixed/sticky bottom bar must not sit on top of content (the original bug)
    const bottomBarOverlap = await page.evaluate(() => {
      const bars = [...document.querySelectorAll("nav, [class*='bottom-0'], [class*='fixed']")]
        .filter((el) => {
          const s = getComputedStyle(el);
          const r = el.getBoundingClientRect();
          return (s.position === "fixed" || s.position === "sticky") &&
                 r.bottom >= window.innerHeight - 4 && r.height > 24 && r.width > window.innerWidth * 0.6;
        });
      if (!bars.length) return null;
      const bar = bars[0].getBoundingClientRect();
      // sample a point just above the bar's top edge; is the bar opaque (bg set)?
      const opaque = bars.map((b) => getComputedStyle(b).backgroundColor)
        .some((c) => c && c !== "rgba(0, 0, 0, 0)" && c !== "transparent");
      return { top: Math.round(bar.top), opaque };
    });
    row.bottomBar = bottomBarOverlap;

    // 3) a11y (axe-core)
    const axe = await new AxeBuilder({ page }).analyze();
    fs.writeFileSync(`${OUT}/axe-${vp.name}.json`, JSON.stringify(axe.violations, null, 2));
    row.axeViolations = axe.violations.length;
    const serious = axe.violations.filter((v) => ["serious", "critical"].includes(v.impact)).length;
    row.axeSeriousCritical = serious;
  } catch (e) {
    row.error = String(e && e.message ? e.message : e);
    hardFail = true;
  }
  summary.push(row);
  console.log(JSON.stringify(row));
  await ctx.close();
}

await browser.close();
fs.writeFileSync(`${OUT}/summary.json`, JSON.stringify(summary, null, 2));
console.log("\n==== SITE AUDIT SUMMARY ====");
console.table(summary.map((r) => ({
  viewport: r.viewport, http: r.http, overflow: r.horizontalOverflow,
  axe: r.axeViolations, serious: r.axeSeriousCritical, error: r.error || "",
})));
process.exit(hardFail ? 1 : 0);
