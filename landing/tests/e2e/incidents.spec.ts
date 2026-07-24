import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("shows exactly two allow and two deny verdicts", async ({ page }) => {
  await page.goto("/");
  const section = page.locator("#incidents");
  await expect(section.locator('[data-verdict="allow"]')).toHaveCount(2);
  await expect(section.locator('[data-verdict="deny"]')).toHaveCount(2);
});

test("tabs switch the incident panel", async ({ page }) => {
  await page.goto("/");
  const section = page.locator("#incidents");

  await expect(section.getByRole("tabpanel")).toContainText(
    "Prompt-regression deployment"
  );

  await section.getByRole("tab", { name: /DB pool/ }).click();
  await expect(section.getByRole("tabpanel")).toContainText(
    "Database pool exhaustion"
  );
});

test("incidents has no critical accessibility violations", async ({ page }) => {
  await page.goto("/");
  const results = await new AxeBuilder({ page }).include("#incidents").analyze();
  expect(results.violations.filter((v) => v.impact === "critical")).toEqual([]);
});
