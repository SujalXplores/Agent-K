import { expect, test } from "@playwright/test";

test("the dynamic open graph image is a 1200x630 png", async ({ request }) => {
  const res = await request.get("/opengraph-image");
  expect(res.status()).toBe(200);
  expect(res.headers()["content-type"]).toContain("image/png");

  const body = await res.body();
  // Parse the PNG IHDR chunk: width at byte offset 16, height at 20 (big-endian).
  const width = body.readUInt32BE(16);
  const height = body.readUInt32BE(20);
  expect(width).toBe(1200);
  expect(height).toBe(630);
});

test("robots.txt resolves and references the sitemap", async ({ request }) => {
  const res = await request.get("/robots.txt");
  expect(res.ok()).toBeTruthy();
  expect(await res.text()).toContain("Sitemap");
});

test("sitemap.xml resolves as a urlset", async ({ request }) => {
  const res = await request.get("/sitemap.xml");
  expect(res.ok()).toBeTruthy();
  expect(await res.text()).toContain("<urlset");
});
