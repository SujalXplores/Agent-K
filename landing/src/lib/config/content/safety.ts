import type { SafetyCard, SectionHeading } from "@/lib/config/content/types";

export interface SafetyContent {
  heading: SectionHeading;
  cards: SafetyCard[];
}

export const safety: SafetyContent = {
  heading: {
    eyebrow: "Safety by construction",
    title: "The sandbox is real, not a promise",
    description:
      "Two design choices make the safety story hold up under scrutiny. Neither depends on trusting the model.",
  },
  cards: [
    {
      id: "isolated-rollback",
      title: "An isolated rollback service",
      description:
        "Agent K never holds the keys to your infrastructure. A separate service does the one thing it is allowed to do.",
      flow: ["Agent K", "POST /rollback", "deployer", "Docker"],
      points: [
        "A small deployer service is the only holder of the Docker access.",
        "Agent K makes one authenticated call that carries no image reference.",
        "The deployer picks the last known-good version and records a marker.",
      ],
    },
    {
      id: "policy-gate",
      title: "A code-only policy gate",
      description:
        "The decision to act lives in plain code that you can read and test. The model is not in the loop.",
      points: [
        "Checks the allowlist, the alert, the cooldown and the confidence.",
        "Checks the cause and the sandbox before anything runs.",
        "Denies the action when any single check fails.",
      ],
    },
  ],
};
