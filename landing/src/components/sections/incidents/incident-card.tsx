import { MagicCard } from "@/components/ui/magic-card";
import type { Incident } from "@/lib/config/content";
import { IncidentChart } from "@/components/sections/incidents/incident-chart";
import { ChartLegend } from "@/components/sections/incidents/chart-legend";
import { VerdictBadge } from "@/components/sections/incidents/verdict-badge";
import { Detail } from "@/components/sections/incidents/detail";

export function IncidentCard({ incident }: { incident: Incident }) {
  const verdictColor =
    incident.verdict === "allow" ? "var(--law-2)" : "var(--destructive)";

  return (
    <MagicCard
      className="rounded-2xl"
      gradientFrom={verdictColor}
      gradientTo={verdictColor}
      gradientColor={verdictColor}
      gradientOpacity={0.08}
    >
      <div className="grid grid-cols-1 gap-6 p-6 sm:p-8 lg:grid-cols-2">
        <div className="flex flex-col gap-4">
          <h3 className="text-xl font-semibold tracking-tight">
            {incident.name}
          </h3>
          <VerdictBadge verdict={incident.verdict} />
          <div className="mt-1 flex flex-col gap-3">
            <Detail label="Symptom" text={incident.symptom} />
            <Detail label="Investigation" text={incident.investigation} />
            <Detail label="Verdict" text={incident.verdictReason} />
          </div>
        </div>

        <div className="flex flex-col justify-center">
          <div className="border-border bg-background/60 rounded-xl border p-4">
            <div className="flex items-center justify-between gap-2">
              <span className="text-muted-foreground font-mono text-[11px] tracking-widest uppercase">
                signoz signal
              </span>
              <span className="text-muted-foreground text-xs">
                {incident.signal}
              </span>
            </div>
            <IncidentChart incident={incident} />
            <ChartLegend incident={incident} />
          </div>
        </div>
      </div>
    </MagicCard>
  );
}
