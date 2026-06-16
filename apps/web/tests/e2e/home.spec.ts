import { test, expect } from "@playwright/test";

test("home route renders the thesis and wordmark", async ({ page }) => {
  const res = await page.goto("/");
  expect(res?.status()).toBe(200);
  await expect(page.getByText("Autonomous Agent")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: /Software delivery\s+that proves itself/i })
  ).toBeVisible();
});
