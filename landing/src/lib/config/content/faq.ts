import type { FaqItem, SectionHeading } from "@/lib/config/content/types";

export interface FaqContent {
  heading: SectionHeading;
  items: FaqItem[];
}

export const faq: FaqContent = {
  heading: {
    eyebrow: "Questions",
    title: "Straight answers for a careful reviewer",
  },
  items: [
    {
      question: "Is this just a chatbot for my logs?",
      answer:
        "No. Agent K is a workflow that produces evidence and takes one careful action. There is no free-form chat box. The output is a structured report with links you can click.",
    },
    {
      question: "What can Agent K actually change in production?",
      answer:
        "Exactly one thing: roll back to the previous version. That is the only action on the allowlist, and it runs only when every safety check passes.",
    },
    {
      question: "How do I know a finding is real?",
      answer:
        "Every claim links to the SigNoz data that supports it. A link checker confirms each link resolves against the running SigNoz instance, so claims without proof never ship.",
    },
    {
      question: "What stops it from acting on a bad guess?",
      answer:
        "A policy written in plain code makes the allow or deny call, with no model involvement. By design, two of the four test incidents are refused a rollback.",
    },
    {
      question: "How is the rollback kept safe?",
      answer:
        "A separate deployer service is the only part that can touch Docker. Agent K just makes one authenticated call that carries no image reference. Its worst case is a single request to a service that does one fixed thing.",
    },
    {
      question: "What if it loops or runs up a large bill?",
      answer:
        "A loop breaker stops repeated queries and a cost watchdog caps spend. When either trips, Agent K stops, marks the investigation incomplete, and escalates with the evidence it has so far.",
    },
    {
      question: "Does it work on any incident?",
      answer:
        "We report results honestly as four out of four on four controlled scenarios, not as general production accuracy. The scenarios are seeded on purpose so the behavior is reproducible.",
    },
    {
      question: "Which SigNoz features does it use?",
      answer:
        "Traces, metrics, logs, dashboards and alerts, plus the Model Context Protocol server for queries, deployment markers, and trace-to-log correlation. SigNoz is the center of the whole system.",
    },
  ],
};
