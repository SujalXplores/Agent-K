import { siteConfig } from "@/lib/config/site";
import type { Cta, TerminalLine } from "@/lib/config/content/types";

export interface HeroContent {
  badge: string;
  headlineLead: string;
  headlineEmphasis: string;
  subhead: string;
  primaryCta: Cta;
  secondaryCta: Cta;
  note: string;
  demo: {
    title: string;
    poster: string;
    note: string;
  };
  terminal: {
    title: string;
    lines: TerminalLine[];
  };
}

export const hero: HeroContent = {
  badge: "Built for the Agents of SigNoz hackathon",
  headlineLead: "Don't just trust an AI agent.",
  headlineEmphasis: "Make it prove every step.",
  subhead:
    "Agent K investigates problems in your AI app, backs up every finding with proof, and only acts when the safety rules say it is safe.",
  primaryCta: { label: "View on GitHub", href: siteConfig.links.github },
  secondaryCta: { label: "Watch the demo", href: siteConfig.links.demo },
  note: "Evidence-backed findings. One safe action. Every decision on the record.",
  demo: {
    title: "Watch the demo",
    poster: "Demo recording coming soon.",
    note: "The full walkthrough lands with the submission. For now, read the code and follow the build blog.",
  },
  terminal: {
    title: "agent-k · investigation",
    lines: [
      { kind: "alert", text: "alert received: error rate breached the objective" },
      { kind: "query", text: "query SigNoz: failed traces after deploy v2" },
      { kind: "evidence", text: "evidence: 214 failed spans linked to deploy v2" },
      { kind: "query", text: "query SigNoz: deployment marker for support-api" },
      { kind: "evidence", text: "evidence: prompt template changed at 10:02" },
      { kind: "muted", text: "confidence recalibrated by code: 0.94" },
      { kind: "verdict-allow", text: "policy gate: ALLOW rollback (all checks pass)" },
      { kind: "action", text: "action: roll back to previous version" },
      { kind: "verify", text: "verified: error rate back to normal" },
    ],
  },
};
