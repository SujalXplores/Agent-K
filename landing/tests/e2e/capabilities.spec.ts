import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const TAGS = ["Evidence feed", "SigNoz over MCP", "Self-telemetry", "Guardrails"];

test("shows four capability tiles from config", async ({ page }) => {
  await page.goto("/");
  const section = page.locator("#capabilities");
  for (const tag of TAGS) {
    await expect(section.getByText(tag, { exact: true })).toBeVisible();
  }
});

test("self-telemetry numbers reach their targets", async ({ page }) => {
  await page.goto("/");
  const section = page.locator("#capabilities");
  await section.scrollIntoViewIfNeeded();
  await expect(section.getByText("18.2k")).toBeVisible({ timeout: 6000 });
  await expect(section.getByText("42s")).toBeVisible({ timeout: 6000 });
});

test("settles on final telemetry values and shows the full evidence feed", async ({
  page,
}) => {
  await page.goto("/");
  const section = page.locator("#capabilities");
  await section.scrollIntoViewIfNeeded();
  await expect(section.getByText("18.2k")).toBeVisible({ timeout: 8000 });
  await expect(section.getByText("42s")).toBeVisible({ timeout: 8000 });
  await expect(
    section.getByText("214 failed spans linked to deploy v2")
  ).toBeVisible({ timeout: 8000 });
  await expect(
    section.getByText("retries doubled within five minutes")
  ).toBeVisible({ timeout: 8000 });
});

test("capability tiles stack in one column on mobile", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 });
  await page.goto("/");
  const headings = page.locator("#capabilities h3");
  const first = await headings.nth(0).boundingBox();
  const second = await headings.nth(1).boundingBox();
  expect(second!.y).toBeGreaterThan(first!.y + 20);
  expect(Math.abs(second!.x - first!.x)).toBeLessThan(5);
});

test("capabilities has no critical accessibility violations", async ({
  page,
}) => {
  await page.goto("/");
  const results = await new AxeBuilder({ page })
    .include("#capabilities")
    .analyze();
  expect(results.violations.filter((v) => v.impact === "critical")).toEqual([]);
});
