import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const QUESTIONS = [
  "Is this just a chatbot for my logs?",
  "What can Agent K actually change in production?",
  "How do I know a finding is real?",
  "What stops it from acting on a bad guess?",
  "How is the rollback kept safe?",
  "What if it loops or runs up a large bill?",
  "Does it work on any incident?",
  "Which SigNoz features does it use?",
];

test("renders all faq questions and answers", async ({ page }) => {
  await page.goto("/");
  const section = page.locator("#faq");

  await expect(section.getByRole("button")).toHaveCount(8);
  for (const question of QUESTIONS) {
    await expect(section.getByRole("button", { name: question })).toBeVisible();
  }

  await expect(
    section.getByText(/There is no free-form chat box/)
  ).toHaveCount(1);
  await expect(
    section.getByText(/SigNoz is the center of the whole system/)
  ).toHaveCount(1);
});

test("faq opens one panel at a time", async ({ page }) => {
  await page.goto("/");
  const section = page.locator("#faq");
  const q1 = section.getByRole("button", { name: QUESTIONS[0] });
  const q2 = section.getByRole("button", { name: QUESTIONS[1] });

  await q1.click();
  await expect(q1).toHaveAttribute("aria-expanded", "true");

  await q2.click();
  await expect(q2).toHaveAttribute("aria-expanded", "true");
  await expect(q1).toHaveAttribute("aria-expanded", "false");
});

test("faq triggers are keyboard operable", async ({ page }) => {
  await page.goto("/");
  const section = page.locator("#faq");
  const q1 = section.getByRole("button", { name: QUESTIONS[0] });
  await q1.focus();
  await page.keyboard.press("Enter");
  await expect(q1).toHaveAttribute("aria-expanded", "true");
});

test("faq has no critical accessibility violations", async ({ page }) => {
  await page.goto("/");
  const results = await new AxeBuilder({ page }).include("#faq").analyze();
  expect(results.violations.filter((v) => v.impact === "critical")).toEqual([]);
});
