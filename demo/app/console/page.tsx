import type { Metadata } from "next";
import { Console } from "@/components/console/console";

export const metadata: Metadata = {
  title: "Agent K · demo console",
  description:
    "Run each seeded incident and watch Agent K's evidence, policy gate and self-telemetry decide what happens.",
};

/**
 * The operator surface, deliberately separate from the customer help centre at
 * `/`. Link values are read on the server so the console never needs to know the
 * RAG service's address — only the public report/dashboard URLs, which are
 * NEXT_PUBLIC by nature.
 */
export default function ConsolePage() {
  return (
    <Console
      links={{
        reports: process.env.NEXT_PUBLIC_REPORTS_URL,
        dashboard: process.env.NEXT_PUBLIC_SIGNOZ_DASHBOARD_URL,
      }}
    />
  );
}
