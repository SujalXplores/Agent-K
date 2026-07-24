import type { Incident, SectionHeading } from "@/lib/config/content/types";

export interface IncidentsContent {
  heading: SectionHeading;
  honesty: string;
  items: Incident[];
}

export const incidents: IncidentsContent = {
  heading: {
    eyebrow: "Four controlled incidents",
    title: "Two safe to fix, two safe to refuse",
    description:
      "Each incident is seeded on purpose as a controlled test. Agent K approves a rollback twice and refuses it twice, and it explains why each time.",
  },
  honesty:
    "Reported honestly as four out of four on four controlled scenarios, not as general production accuracy.",
  items: [
    {
      id: "prompt-regression",
      index: 1,
      name: "Prompt-regression deployment",
      tag: "Prompt regression",
      symptom:
        "A broken prompt template ships in a new version and failed answers rise right after the deploy.",
      investigation:
        "Agent K connects the error spike to the deployment marker and shows the failed traces.",
      verdict: "allow",
      verdictReason:
        "The cause is a recent deployment and the error budget is breached, so a rollback is allowed.",
      signal: "Error rate spikes after deploy v2",
      series: [8, 9, 10, 9, 42, 61, 66, 63],
      threshold: 25,
      deployAt: 3.5,
      unit: "err/min",
    },
    {
      id: "retry-storm",
      index: 2,
      name: "Retry-storm cost runaway",
      tag: "Cost runaway",
      symptom:
        "A config change lowers timeouts, so the app retries model calls and cost per minute climbs fast.",
      investigation:
        "Agent K finds the repeated-call pattern and ties the cost breach to the new deployment.",
      verdict: "allow",
      verdictReason:
        "A cost budget breach tied to a deployment is enough to justify a rollback, even with few user errors.",
      signal: "Cost per minute breaks the budget",
      series: [12, 13, 14, 22, 38, 55, 72, 80],
      threshold: 50,
      deployAt: 2.5,
      unit: "$/min",
    },
    {
      id: "retrieval-latency",
      index: 3,
      name: "Retrieval latency injection",
      tag: "Latency",
      symptom:
        "A flag adds delay to the database search step, so overall response time climbs with no new deploy.",
      investigation:
        "The trace waterfall points to the retrieval step as the bottleneck, with no deployment cause.",
      verdict: "deny",
      verdictReason:
        "There is no deployment to undo, so a rollback would not help. Agent K escalates to a human.",
      signal: "Retrieval step dominates the trace",
      series: [30, 32, 31, 33, 34, 32, 33, 31],
      unit: "% of trace",
    },
    {
      id: "pool-exhaustion",
      index: 4,
      name: "Database pool exhaustion",
      tag: "DB pool",
      symptom:
        "Too few database connections are configured, so errors rise and logs show the pool is exhausted.",
      investigation:
        "Agent K links the pool errors in logs to the failed traces and explains the failure type.",
      verdict: "deny",
      verdictReason:
        "Rolling back the app version does not fix a connection limit, so Agent K recommends a human change.",
      signal: "Connection-pool errors fill the logs",
      series: [10, 14, 26, 40, 44, 52, 58, 60],
      threshold: 30,
      unit: "err/min",
    },
  ],
};
