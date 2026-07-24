import { describe, expect, it } from "vitest";

import { content } from "@/lib/config/content";
import { siteConfig } from "@/lib/config/site";
import { techStack } from "@/lib/config/tech-stack";

describe("siteConfig", () => {
  it("has the core identity fields", () => {
    expect(siteConfig.name).toBe("Agent K");
    expect(siteConfig.url).toMatch(/^https?:\/\//);
    expect(siteConfig.description.length).toBeGreaterThan(50);
  });

  it("exposes navigation anchors and a github link", () => {
    expect(siteConfig.nav.length).toBeGreaterThan(0);
    for (const item of siteConfig.nav) {
      expect(item.href.startsWith("#")).toBe(true);
      expect(item.label.length).toBeGreaterThan(0);
    }
    expect(siteConfig.links.github).toContain("github.com");
  });
});

describe("content structure", () => {
  it("defines exactly three laws with distinct accents and examples", () => {
    const laws = content.laws.items;
    expect(laws).toHaveLength(3);
    expect(laws.map((l) => l.id)).toEqual(["law-1", "law-2", "law-3"]);
    for (const law of laws) {
      expect(law.points.length).toBeGreaterThan(0);
      expect(law.example).toBeDefined();
      expect(law.principle.length).toBeGreaterThan(0);
    }
  });

  it("defines ten pipeline steps in order", () => {
    const steps = content.howItWorks.steps;
    expect(steps).toHaveLength(10);
    steps.forEach((step, i) => {
      expect(step.index).toBe(i + 1);
      expect(step.title.length).toBeGreaterThan(0);
    });
  });

  it("defines four incidents with exactly two allow and two deny", () => {
    const incidents = content.incidents.items;
    expect(incidents).toHaveLength(4);
    const allow = incidents.filter((i) => i.verdict === "allow");
    const deny = incidents.filter((i) => i.verdict === "deny");
    expect(allow).toHaveLength(2);
    expect(deny).toHaveLength(2);
  });

  it("defines four capabilities and two safety cards", () => {
    expect(content.capabilities.items).toHaveLength(4);
    expect(content.safety.cards).toHaveLength(2);
  });

  it("defines a set of FAQ items", () => {
    expect(content.faq.items.length).toBeGreaterThanOrEqual(6);
    for (const item of content.faq.items) {
      expect(item.question.length).toBeGreaterThan(0);
      expect(item.answer.length).toBeGreaterThan(0);
    }
  });
});

describe("techStack", () => {
  it("lists the eight real technologies with links and icons", () => {
    expect(techStack).toHaveLength(8);
    for (const tech of techStack) {
      expect(tech.name.length).toBeGreaterThan(0);
      expect(tech.href).toMatch(/^https?:\/\//);
      expect(tech.icon.length).toBeGreaterThan(0);
    }
  });
});

describe("copy standard", () => {
  it("contains no em dashes or en dashes anywhere in the copy", () => {
    const serialized = JSON.stringify(content) + JSON.stringify(siteConfig);
    expect(serialized).not.toContain("\u2014"); // em dash
    expect(serialized).not.toContain("\u2013"); // en dash
  });

  it("does not leave common acronyms unexplained in visible copy", () => {
    const serialized = JSON.stringify(content);
    for (const acronym of ["SLO", "UTC", "RCA"]) {
      expect(serialized).not.toMatch(new RegExp(`\\b${acronym}\\b`));
    }
  });
});
