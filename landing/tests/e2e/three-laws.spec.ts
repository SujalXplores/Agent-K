import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("renders three laws with correct accent, titles and examples", async ({
  page,
}) => {
  await page.goto("/");
  const section = page.locator("#laws");

  await expect(section.locator("h3")).toHaveCount(3);

  // Correct accent colour per law.
  await expect(section.getByText("Law 1", { exact: true })).toHaveClass(
    /text-law-1/
  );
  await expect(section.getByText("Law 2", { exact: true })).toHaveClass(
    /text-law-2/
  );
  await expect(section.getByText("Law 3", { exact: true })).toHaveClass(
    /text-law-3/
  );

  await expect(
    section.getByRole("heading", { name: "No claim without evidence" })
  ).toBeVisible();
  await expect(
    section.getByRole("heading", { name: "No action without budget" })
  ).toBeVisible();
  await expect(
    section.getByRole("heading", { name: "No self without telemetry" })
  ).toBeVisible();

  // Per-law examples: evidence confidence, allow/deny boxes, telemetry note.
  await expect(section.getByText("confidence 0.94")).toBeVisible();
  await expect(
    section.getByText("All checks pass", { exact: true })
  ).toBeVisible();
  await expect(
    section.getByText("Any check fails", { exact: true })
  ).toBeVisible();
  await expect(
    section.getByText("Sample values shown for illustration, not fixed targets.")
  ).toBeVisible();
});

test("law cards stack on mobile", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 });
  await page.goto("/");
  const headings = page.locator("#laws h3");
  const first = await headings.nth(0).boundingBox();
  const second = await headings.nth(1).boundingBox();
  expect(second!.y).toBeGreaterThan(first!.y + 20);
});

test("laws section has no critical accessibility violations", async ({
  page,
}) => {
  await page.goto("/");
  const results = await new AxeBuilder({ page }).include("#laws").analyze();
  expect(results.violations.filter((v) => v.impact === "critical")).toEqual([]);
});
