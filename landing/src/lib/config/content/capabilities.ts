import type { Capability, SectionHeading } from "@/lib/config/content/types";

export interface CapabilitiesContent {
  heading: SectionHeading;
  items: Capability[];
  evidenceFeed: { kind: string; text: string }[];
  telemetry: {
    note: string;
    metrics: {
      label: string;
      prefix: string;
      value: number;
      decimals: number;
      suffix: string;
    }[];
  };
  flow: string[];
  guardrails: { label: string; detail: string }[];
}

export const capabilities: CapabilitiesContent = {
  heading: {
    eyebrow: "What it does",
    title: "An investigator you can actually check",
    description:
      "Agent K is not a chatbot for your logs. It is a workflow that produces evidence, takes one careful action, and watches its own work.",
  },
  items: [
    {
      id: "evidence",
      tag: "Evidence feed",
      title: "Every finding comes with proof",
      description:
        "Each claim links straight to the traces, logs, metrics or deployment that back it up. No proof, no claim.",
    },
    {
      id: "investigate",
      tag: "SigNoz over MCP",
      title: "Investigates through SigNoz",
      description:
        "Agent K asks SigNoz for evidence through the Model Context Protocol (MCP). Every query is recorded as its own step.",
    },
    {
      id: "self-telemetry",
      tag: "Self-telemetry",
      title: "Watches its own work",
      description:
        "It records its own cost, tokens, time and queries, so you can audit how it reached an answer.",
    },
    {
      id: "guardrails",
      tag: "Guardrails",
      title: "Knows when to stop",
      description:
        "A loop breaker halts repeated queries and a cost watchdog caps spend. When either trips, it escalates to a human.",
    },
  ],
  evidenceFeed: [
    { kind: "trace", text: "214 failed spans linked to deploy v2" },
    { kind: "deployment", text: "prompt template changed at 10:02" },
    { kind: "metric", text: "error rate climbed above the objective" },
    { kind: "log", text: "retries doubled within five minutes" },
  ],
  telemetry: {
    note: "Sample values, shown for illustration.",
    metrics: [
      { label: "cost per run", prefix: "$", value: 0.004, decimals: 3, suffix: "" },
      { label: "tokens used", prefix: "", value: 18.2, decimals: 1, suffix: "k" },
      { label: "seconds to answer", prefix: "", value: 42, decimals: 0, suffix: "s" },
    ],
  },
  flow: ["Agent K", "MCP", "SigNoz"],
  guardrails: [
    { label: "Loop breaker", detail: "Stops repeated queries" },
    { label: "Cost watchdog", detail: "Caps spend per run" },
  ],
};
