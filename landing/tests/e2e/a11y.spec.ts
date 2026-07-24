import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

async function criticalViolations(selector: string, page: Page) {
  const results = await new AxeBuilder({ page }).include(selector).analyze();
  return results.violations.filter((v) => v.impact === "critical");
}

test("navbar has no critical accessibility violations", async ({ page }) => {
  await page.goto("/");
  expect(await criticalViolations("header", page)).toEqual([]);
});

test("footer has no critical accessibility violations", async ({ page }) => {
  await page.goto("/");
  expect(await criticalViolations("footer", page)).toEqual([]);
});

for (const theme of ["dark", "light"] as const) {
  test(`full page has no critical or serious violations (${theme})`, async ({
    page,
  }) => {
    // Entrance reveals and the hero terminal animate for every visitor, so the
    // scan must run once everything has settled: scroll through the page to
    // trigger all in-view reveals, then wait for the terminal to finish typing.
    // Reduced motion is still emulated to keep looping accents (shimmer, spin)
    // frozen for a deterministic colour-contrast frame.
    await page.emulateMedia({ reducedMotion: "reduce" });
    if (theme === "light") {
      await page.addInitScript(() => localStorage.setItem("theme", "light"));
    }
    await page.goto("/");

    await page.evaluate(async () => {
      for (let y = 0; y <= document.body.scrollHeight; y += 400) {
        window.scrollTo(0, y);
        await new Promise((r) => setTimeout(r, 60));
      }
      window.scrollTo(0, 0);
    });

    // Wait for the terminal's final line to reach full opacity (sequence done).
    await page
      .waitForFunction(
        () => {
          const el = Array.from(document.querySelectorAll("span")).find(
            (n) => n.textContent === "verified: error rate back to normal"
          );
          if (!el) return false;
          let node: HTMLElement | null = el;
          while (node && node !== document.body) {
            if (parseFloat(getComputedStyle(node).opacity) < 0.99) return false;
            node = node.parentElement;
          }
          return true;
        },
        { timeout: 15000 }
      )
      .catch(() => {});
    await page.waitForTimeout(500);

    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();
    const blocking = results.violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious"
    );
    expect(blocking).toEqual([]);
  });
}
