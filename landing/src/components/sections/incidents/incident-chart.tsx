import type { Incident } from "@/lib/config/content";
import { buildChartPaths } from "@/components/sections/incidents/chart-utils";

export function IncidentChart({ incident }: { incident: Incident }) {
  const { threshold, deployAt } = incident;
  const { W, H, top, plot, xFor, yFor, line, area } = buildChartPaths(incident);
  const gradientId = `spark-${incident.id}`;

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="none"
      className="mt-3 h-24 w-full"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--chart-5)" stopOpacity="0.3" />
          <stop offset="100%" stopColor="var(--chart-5)" stopOpacity="0" />
        </linearGradient>
      </defs>
      {[0.33, 0.66].map((f) => (
        <line
          key={f}
          x1="0"
          y1={top + f * plot}
          x2={W}
          y2={top + f * plot}
          stroke="var(--border)"
          strokeWidth={1}
          strokeOpacity={0.6}
          vectorEffect="non-scaling-stroke"
        />
      ))}
      {threshold != null && (
        <line
          x1="0"
          y1={yFor(threshold)}
          x2={W}
          y2={yFor(threshold)}
          stroke="var(--destructive)"
          strokeWidth={1}
          strokeDasharray="4 3"
          vectorEffect="non-scaling-stroke"
        />
      )}
      {deployAt != null && (
        <line
          x1={xFor(deployAt)}
          y1="0"
          x2={xFor(deployAt)}
          y2={H}
          stroke="var(--foreground)"
          strokeOpacity={0.4}
          strokeWidth={1}
          strokeDasharray="3 2"
          vectorEffect="non-scaling-stroke"
        />
      )}
      <path d={area} fill={`url(#${gradientId})`} />
      <path
        d={line}
        fill="none"
        stroke="var(--chart-5)"
        strokeWidth={1.75}
        strokeLinecap="round"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}
