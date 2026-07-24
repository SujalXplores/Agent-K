import type { Incident } from "@/lib/config/content";

export function ChartLegend({ incident }: { incident: Incident }) {
  return (
    <div className="text-muted-foreground mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 font-mono text-[10px]">
      <span className="inline-flex items-center gap-1.5">
        <span className="bg-chart-5 h-0.5 w-3 rounded-full" />
        signal
      </span>
      {incident.threshold != null && (
        <span className="inline-flex items-center gap-1.5">
          <span className="border-destructive h-0 w-3 border-t border-dashed" />
          objective
        </span>
      )}
      {incident.deployAt != null && (
        <span className="inline-flex items-center gap-1.5">
          <span className="border-foreground/50 h-3 w-0 border-l border-dashed" />
          deploy v2
        </span>
      )}
      <span className="text-foreground ml-auto">
        peak {Math.max(...incident.series)}
        {incident.unit ? ` ${incident.unit}` : ""}
      </span>
    </div>
  );
}
