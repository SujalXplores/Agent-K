import { siteConfig } from "@/lib/config/site";
import type { Cta } from "@/lib/config/content/types";

export interface CtaContent {
  eyebrow: string;
  headline: string;
  headlineEmphasis: string;
  subhead: string;
  primary: Cta;
  secondary: Cta;
  blog: Cta;
}

export const cta: CtaContent = {
  eyebrow: "See it for yourself",
  headline: "Prove what it knows.",
  headlineEmphasis: "Earn the right to act.",
  subhead:
    "Read the code, watch the demo, and follow the build. Agent K shows its work at every step.",
  primary: { label: "View on GitHub", href: siteConfig.links.github },
  secondary: { label: "Watch the demo", href: siteConfig.links.demo },
  blog: { label: "Read the build blog", href: siteConfig.links.blog },
};
