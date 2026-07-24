import { siteConfig } from "@/lib/config/site";

export interface FooterColumn {
  title: string;
  links: { label: string; href: string }[];
}

export interface FooterContent {
  tagline: string;
  disclosure: string;
  columns: FooterColumn[];
}

export const footer: FooterContent = {
  tagline:
    "An incident-response agent that proves every finding and earns the right to act.",
  disclosure:
    "Built with AI assistance and disclosed per the hackathon rules. Results are reported honestly as four out of four on four controlled scenarios.",
  columns: [
    {
      title: "Explore",
      links: [
        { label: "Capabilities", href: "#capabilities" },
        { label: "The Three Laws", href: "#laws" },
        { label: "How it works", href: "#how-it-works" },
        { label: "Incidents", href: "#incidents" },
      ],
    },
    {
      title: "Project",
      links: [
        { label: "GitHub", href: siteConfig.links.github },
        { label: "Build blog", href: siteConfig.links.blog },
        { label: "Watch the demo", href: siteConfig.links.demo },
      ],
    },
    {
      title: "Built on",
      links: [
        { label: "SigNoz", href: siteConfig.links.signoz },
        { label: "OpenTelemetry", href: siteConfig.links.openTelemetry },
        { label: "The hackathon", href: siteConfig.links.signozHackathon },
      ],
    },
  ],
};
