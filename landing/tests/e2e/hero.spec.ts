import { expect, test } from "@playwright/test";

const GITHUB_URL = "https://github.com/agent-k-dev/agent-k";

test("hero shows the headline and a GitHub CTA linked from config", async ({
  page,
}) => {
  await page.goto("/");

  const heading = page.getByRole("heading", { level: 1 });
  await expect(heading).toContainText("Don't just trust an AI agent");
  await expect(heading).toContainText("Make it prove every step");

  const cta = page.getByRole("link", { name: /View on GitHub/i }).first();
  await expect(cta).toHaveAttribute("href", GITHUB_URL);
});

test("demo dialog opens, traps focus, and closes on Escape", async ({
  page,
}) => {
  await page.goto("/");

  await page.getByRole("button", { name: "Watch the demo" }).first().click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();

  const focusInside = await dialog.evaluate((el) =>
    el.contains(document.activeElement)
  );
  expect(focusInside).toBe(true);

  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
});

test("terminal renders its full investigation, ending on the verified line", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByText("verified: error rate back to normal")
  ).toBeVisible({ timeout: 6000 });
});

test.describe("responsive hero", () => {
  for (const width of [375, 768, 1280]) {
    test(`no horizontal overflow at ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 });
      await page.goto("/");

      const overflow = await page.evaluate(
        () =>
          document.documentElement.scrollWidth -
          document.documentElement.clientWidth
      );
      expect(overflow).toBeLessThanOrEqual(1);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    });
  }
});
