import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("renders both safety cards with the rollback flow", async ({ page }) => {
  await page.goto("/");
  const section = page.locator("#safety");

  await expect(
    section.getByRole("heading", { name: "An isolated rollback service" })
  ).toBeVisible();
  await expect(
    section.getByRole("heading", { name: "A code-only policy gate" })
  ).toBeVisible();

  for (const node of ["Agent K", "POST /rollback", "deployer", "Docker"]) {
    await expect(section.getByText(node, { exact: true })).toBeVisible();
  }
});

test("safety cards stack on mobile", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 });
  await page.goto("/");
  const headings = page.locator("#safety h3");
  const first = await headings.nth(0).boundingBox();
  const second = await headings.nth(1).boundingBox();
  expect(second!.y).toBeGreaterThan(first!.y + 20);
});

test("safety has no critical accessibility violations", async ({ page }) => {
  await page.goto("/");
  const results = await new AxeBuilder({ page }).include("#safety").analyze();
  expect(results.violations.filter((v) => v.impact === "critical")).toEqual([]);
});
