import { expect, test } from "@playwright/test";

test("the home page loads and renders content", async ({ page }) => {
  const response = await page.goto("/");
  expect(response?.ok()).toBeTruthy();
  await expect(page.locator("body")).toBeVisible();
});
