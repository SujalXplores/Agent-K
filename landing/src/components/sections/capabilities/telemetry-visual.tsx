import { NumberTicker } from "@/components/ui/number-ticker";
import { content } from "@/lib/config/content";

export function TelemetryVisual() {
  const { metrics, note } = content.capabilities.telemetry;

  return (
    <div className="flex w-full flex-col gap-4">
      <div className="grid grid-cols-3 gap-3">
        {metrics.map((metric) => (
          <div
            key={metric.label}
            className="border-border bg-background/60 flex flex-col gap-1 rounded-lg border p-3"
          >
            <span className="text-foreground font-mono text-xl font-semibold tabular-nums sm:text-2xl">
              {metric.prefix}
              <NumberTicker
                value={metric.value}
                decimalPlaces={metric.decimals}
                className="text-foreground"
              />
              {metric.suffix}
            </span>
            <span className="text-muted-foreground text-[11px]">
              {metric.label}
            </span>
          </div>
        ))}
      </div>
      <p className="text-muted-foreground font-mono text-[11px]">{note}</p>
    </div>
  );
}
