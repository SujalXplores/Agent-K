import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const TITLES = [
  "Alert received",
  "Collect evidence",
  "Investigate",
  "Find possible causes",
  "Attach evidence",
  "Check the safety policy",
  "Take action if allowed",
  "Verify the result",
  "Create the report",
  "Observe itself",
];

test("desktop pipeline is an ordered list of ten steps in order", async ({
  page,
}) => {
  await page.goto("/");
  const items = page.locator("#how-it-works ol > li");
  await expect(items).toHaveCount(10);
  for (let i = 0; i < TITLES.length; i++) {
    await expect(items.nth(i)).toContainText(TITLES[i]);
  }
});

test("mobile stepper switches panels", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  const section = page.locator("#how-it-works");

  await expect(section.getByRole("tabpanel")).toContainText(
    "A SigNoz alert fires and reaches Agent K over a webhook."
  );

  await section.getByRole("tab", { name: "6", exact: true }).click();
  await expect(section.getByRole("tabpanel")).toContainText(
    "Code checks whether a safe rollback is allowed."
  );
});

test("reduced motion still shows all pipeline steps", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await expect(page.locator("#how-it-works ol > li")).toHaveCount(10);
});

test("how it works has no critical accessibility violations", async ({
  page,
}) => {
  await page.goto("/");
  const results = await new AxeBuilder({ page })
    .include("#how-it-works")
    .analyze();
  expect(results.violations.filter((v) => v.impact === "critical")).toEqual([]);
});
