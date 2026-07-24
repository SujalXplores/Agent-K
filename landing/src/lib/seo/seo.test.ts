import { describe, expect, it } from "vitest";

import robots from "@/app/robots";
import sitemap from "@/app/sitemap";
import { siteConfig } from "@/lib/config/site";
import { OG_CONTENT_TYPE, OG_SIZE } from "@/lib/seo/og";

describe("open graph image contract", () => {
  it("is 1200x630 and a png", () => {
    expect(OG_SIZE).toEqual({ width: 1200, height: 630 });
    expect(OG_CONTENT_TYPE).toBe("image/png");
  });
});

describe("sitemap", () => {
  it("includes the canonical site url", () => {
    const entries = sitemap();
    expect(entries.length).toBeGreaterThan(0);
    expect(entries[0].url).toBe(siteConfig.url);
  });
});

describe("robots", () => {
  it("allows all crawlers and points to the sitemap", () => {
    const result = robots();
    const rules = Array.isArray(result.rules) ? result.rules : [result.rules];
    expect(rules[0].userAgent).toBe("*");
    expect(rules[0].allow).toBe("/");
    expect(result.sitemap).toBe(`${siteConfig.url}/sitemap.xml`);
  });
});
