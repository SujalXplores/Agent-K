const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, "") ??
  "https://agent-k.vercel.app";

export interface NavItem {
  label: string;
  href: string;
}

export const siteConfig = {
  name: "Agent K",
  shortName: "Agent K",
  title: "Agent K: prove every step, then act",
  titleTemplate: "%s · Agent K",
  description:
    "Agent K is an incident-response agent that investigates problems in your AI app, backs every finding with SigNoz evidence, and only acts when code-based safety rules allow it.",
  tagline: "Don't just trust an AI agent. Make it prove every step.",
  url: SITE_URL,
  locale: "en_US",
  themeColor: {
    light: "#ffffff",
    dark: "#0b1020",
  },
  creator: "The Agent K team",
  ogImageAlt:
    "Agent K: an incident-response agent that proves every finding with evidence and only acts when safety rules allow.",
  keywords: [
    "Agent K",
    "AI incident response",
    "AI agent observability",
    "SigNoz",
    "OpenTelemetry",
    "AIOps",
    "root cause analysis",
    "evidence-backed AI",
    "agent safety",
    "Model Context Protocol",
    "AI SRE",
  ],
  links: {
    github: "https://github.com/agent-k-dev/agent-k",
    demo: "",
    blog: "https://dev.to/agent-k",
    signozHackathon: "https://www.wemakedevs.org/hackathons/signoz",
    signoz: "https://signoz.io",
    openTelemetry: "https://opentelemetry.io",
  },
  nav: [
    { label: "Capabilities", href: "#capabilities" },
    { label: "The Three Laws", href: "#laws" },
    { label: "How it works", href: "#how-it-works" },
    { label: "Incidents", href: "#incidents" },
    { label: "FAQ", href: "#faq" },
  ] satisfies NavItem[],
} as const;

export type SiteConfig = typeof siteConfig;
