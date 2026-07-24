import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const GITHUB = "https://github.com/agent-k-dev/agent-k";
const BLOG = "https://dev.to/agent-k";

test("cta links come from config and the closing line renders", async ({
  page,
}) => {
  await page.goto("/");
  const section = page.locator("#cta");

  await expect(section.getByRole("heading", { level: 2 })).toContainText(
    "Earn the right to act"
  );

  await expect(
    section.getByRole("link", { name: /View on GitHub/i })
  ).toHaveAttribute("href", GITHUB);
  await expect(
    section.getByRole("link", { name: /Read the build blog/i })
  ).toHaveAttribute("href", BLOG);

  await expect(
    section.getByRole("button", { name: "Watch the demo" })
  ).toBeVisible();
});

test("cta has no critical accessibility violations", async ({ page }) => {
  await page.goto("/");
  const results = await new AxeBuilder({ page }).include("#cta").analyze();
  expect(results.violations.filter((v) => v.impact === "critical")).toEqual([]);
});

test("cta has no horizontal overflow on mobile", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 });
  await page.goto("/");
  const overflow = await page.evaluate(
    () =>
      document.documentElement.scrollWidth -
      document.documentElement.clientWidth
  );
  expect(overflow).toBeLessThanOrEqual(1);
});
