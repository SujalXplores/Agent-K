import { expect, test } from "@playwright/test";

const TECH = [
  { name: "SigNoz", href: "https://signoz.io" },
  { name: "OpenTelemetry", href: "https://opentelemetry.io" },
  { name: "FastAPI", href: "https://fastapi.tiangolo.com" },
  { name: "Groq", href: "https://groq.com" },
  {
    name: "PostgreSQL + pgvector",
    href: "https://github.com/pgvector/pgvector",
  },
  { name: "Docker", href: "https://www.docker.com" },
  { name: "Python", href: "https://www.python.org" },
  { name: "Model Context Protocol", href: "https://modelcontextprotocol.io" },
];

test("tech row links each technology with the right href", async ({ page }) => {
  await page.goto("/");
  const section = page.locator("#stack");

  // The marquee repeats its children for a seamless loop, so each technology
  // appears more than once; assert the first linked node per technology.
  for (const tech of TECH) {
    const link = section
      .getByRole("link", { name: tech.name, exact: true })
      .first();
    await expect(link).toHaveAttribute("href", tech.href);
  }
});

test("marquee pauses on hover", async ({ page }) => {
  await page.goto("/");
  // Hover the stable marquee container (the rows themselves never stop moving,
  // so they cannot be hovered directly). Hovering the group pauses the rows.
  const marquee = page.locator("#stack .group").first();
  await marquee.hover();

  const row = marquee.locator(".animate-marquee").first();
  const playState = await row.evaluate(
    (el) => getComputedStyle(el).animationPlayState
  );
  expect(playState).toBe("paused");
});
