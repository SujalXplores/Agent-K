import { expect, test } from "@playwright/test";

test("theme toggle flips and persists across reload", async ({ page }) => {
  await page.goto("/");
  const html = page.locator("html");

  // Dark is the default theme.
  await expect(html).toHaveClass(/dark/);

  await page.getByRole("button", { name: "Toggle color theme" }).first().click();
  await expect(html).not.toHaveClass(/dark/);

  await page.reload();
  await expect(html).not.toHaveClass(/dark/);
});

test("primary nav scrolls to the matching section anchor", async ({ page }) => {
  await page.goto("/");

  await page
    .getByRole("navigation", { name: "Primary" })
    .getByRole("link", { name: "The Three Laws" })
    .click();

  await expect(page).toHaveURL(/#laws$/);
  await expect(page.locator("#laws")).toBeInViewport();
});

test.describe("mobile navigation", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("opens and closes the mobile menu", async ({ page }) => {
    await page.goto("/");

    await page.getByRole("button", { name: "Open menu" }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await expect(
      dialog.getByRole("link", { name: "Capabilities" })
    ).toBeVisible();

    await page.getByRole("button", { name: "Close menu" }).click();
    await expect(dialog).toBeHidden();
  });

  test("selecting a link closes the mobile menu", async ({ page }) => {
    await page.goto("/");

    await page.getByRole("button", { name: "Open menu" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("link", { name: "FAQ" }).click();

    await expect(dialog).toBeHidden();
    await expect(page).toHaveURL(/#faq$/);
  });
});
