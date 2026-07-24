import type { Law, SectionHeading } from "@/lib/config/content/types";

export interface LawsContent {
  heading: SectionHeading;
  items: Law[];
}

export const laws: LawsContent = {
  heading: {
    eyebrow: "The Three Laws",
    title: "Rules enforced by code, not by prompts",
    description:
      "Three simple rules decide what Agent K may claim, what it may do, and what it must record. Software enforces each one.",
  },
  items: [
    {
      id: "law-1",
      index: 1,
      name: "Law 1",
      title: "No claim without evidence",
      principle:
        "Agent K never guesses. Every finding links to the exact data that backs it up.",
      description:
        "A claim must carry its text, a confidence value, the query used, the time range searched, and a link that resolves. The report drops any claim with no evidence.",
      points: [
        "Every claim links to a real SigNoz trace, log, metric or deployment.",
        "A link checker confirms every published link still resolves.",
      ],
      example: {
        kind: "evidence",
        claim: "The v2 prompt template caused the rise in failed answers.",
        confidence: 0.94,
        evidence: [
          { type: "trace", query: "failed requests after deploy v2" },
          { type: "deployment", query: "deployment marker for support-api v2" },
        ],
      },
    },
    {
      id: "law-2",
      index: 2,
      name: "Law 2",
      title: "No action without budget",
      principle:
        "Agent K can do only one thing: undo the last release. And only when every safety check passes.",
      description:
        "Before any action, a code-based policy checks the breach, the allowlist, the cooldown, the confidence, the cause and the sandbox. The model has no say in the verdict.",
      points: [
        "The allowlist holds exactly one action: roll back to the last version.",
        "If any check fails, it acts on nothing and escalates to a human.",
      ],
      example: {
        kind: "policy",
        allow: {
          title: "All checks pass",
          lines: [
            "Objective breached",
            "Cause tied to a deployment",
            "Confidence above threshold",
          ],
        },
        deny: {
          title: "Any check fails",
          lines: [
            "No deployment cause found",
            "Action not on the allowlist",
            "Escalate to a human",
          ],
        },
      },
    },
    {
      id: "law-3",
      index: 3,
      name: "Law 3",
      title: "No self without telemetry",
      principle:
        "Every step is recorded, so you can see what Agent K did, how long it took, and what it cost.",
      description:
        "Agent K watches itself as closely as it watches the app. Cost, tokens, duration, queries, loops and every decision are recorded in SigNoz.",
      points: [
        "Token counts and estimated cost are recorded for every model call.",
        "Loop-breaker and cost-watchdog events are visible in the dashboard.",
      ],
      example: {
        kind: "telemetry",
        metrics: [
          { label: "cost / investigation", value: "$0.004" },
          { label: "tokens", value: "18.2k" },
          { label: "duration", value: "42s" },
          { label: "MCP queries", value: "11" },
        ],
        note: "Sample values shown for illustration, not fixed targets.",
      },
    },
  ],
};
