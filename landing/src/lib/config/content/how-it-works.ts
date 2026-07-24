import type { PipelineStep, SectionHeading } from "@/lib/config/content/types";

export interface HowItWorksContent {
  heading: SectionHeading;
  steps: PipelineStep[];
}

export const howItWorks: HowItWorksContent = {
  heading: {
    eyebrow: "How it works",
    title: "From alert to auditable report",
    description:
      "Ten fixed steps run in order. The model proposes ideas inside some steps, but code decides what happens next.",
  },
  steps: [
    {
      index: 1,
      title: "Alert received",
      description: "A SigNoz alert fires and reaches Agent K over a webhook.",
    },
    {
      index: 2,
      title: "Collect evidence",
      description:
        "It gathers traces, metrics, logs and deployment history through SigNoz.",
    },
    {
      index: 3,
      title: "Investigate",
      description: "It runs a fixed set of queries to narrow down the problem.",
    },
    {
      index: 4,
      title: "Find possible causes",
      description: "It forms one or more root-cause explanations.",
    },
    {
      index: 5,
      title: "Attach evidence",
      description: "It links supporting SigNoz data to every explanation.",
    },
    {
      index: 6,
      title: "Check the safety policy",
      description: "Code checks whether a safe rollback is allowed.",
    },
    {
      index: 7,
      title: "Take action if allowed",
      description: "If the policy approves, it rolls back the last release.",
    },
    {
      index: 8,
      title: "Verify the result",
      description: "It re-queries SigNoz to confirm the app recovered.",
    },
    {
      index: 9,
      title: "Create the report",
      description: "It writes an auditable report with links you can click.",
    },
    {
      index: 10,
      title: "Observe itself",
      description: "It records its own cost, time, queries and decisions.",
    },
  ],
};
