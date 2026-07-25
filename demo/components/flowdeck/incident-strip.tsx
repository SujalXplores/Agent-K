"use client";

import { AlertTriangleIcon, CheckCircle2Icon } from "lucide-react";
import { type FC, useEffect, useState } from "react";
import { SCENARIOS } from "@/lib/flowdeck";
import { cn } from "@/lib/utils";

type FlagsPayload = { flags: Record<string, boolean> | null };

/**
 * Live status strip showing which seeded failure scenario is switched on.
 *
 * This exists for the demo audience, not for Flowdeck's fictional customers: it
 * makes the injected fault legible on screen at the moment it is switched on, so
 * a viewer can connect "the assistant just got worse" to "this specific scenario
 * is live" to "here is what SigNoz recorded" without a narrator explaining it.
 *
 * Hidden entirely when nothing is wrong and when the flag state can't be read,
 * so a healthy demo looks like an ordinary product.
 */
export const IncidentStrip: FC<{ pollMs?: number }> = ({ pollMs = 5000 }) => {
  const [active, setActive] = useState<string[]>([]);
  const [reachable, setReachable] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;
    let cancelled = false;

    const poll = async () => {
      try {
        const response = await fetch("/api/flags", {
          signal: controller.signal,
          cache: "no-store",
        });
        const { flags } = (await response.json()) as FlagsPayload;

        if (cancelled) return;

        if (flags == null) {
          setReachable(false);
        } else {
          setReachable(true);
          setActive(
            Object.entries(flags)
              .filter(([, enabled]) => enabled)
              .map(([name]) => name),
          );
        }
      } catch {
        if (!cancelled) setReachable(false);
      } finally {
        if (!cancelled) timer = setTimeout(poll, pollMs);
      }
    };

    void poll();

    return () => {
      cancelled = true;
      controller.abort();
      if (timer) clearTimeout(timer);
    };
  }, [pollMs]);

  if (!reachable || active.length === 0) return null;

  return (
    <div role="status" className="border-b border-amber-500/25 bg-amber-500/10 px-4 py-2">
      <div className="mx-auto flex max-w-3xl flex-col gap-1.5">
        {active.map((name) => {
          const scenario = SCENARIOS[name];
          return (
            <div
              key={name}
              className="flex items-start gap-2 text-xs text-amber-700 dark:text-amber-300"
            >
              <AlertTriangleIcon className="mt-px size-3.5 shrink-0" aria-hidden />
              <span>
                <span className="font-semibold">{scenario?.label ?? name} active</span>
                {scenario ? ` — ${scenario.symptom}.` : null}
                {scenario ? (
                  <span className="opacity-70">
                    {scenario.deployment
                      ? " Deployment-caused, so a rollback is eligible."
                      : " Not deployment-caused, so a rollback will be denied."}
                  </span>
                ) : null}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

/** Small always-on badge for the header, showing service reachability. */
export const ServiceBadge: FC<{ healthy: boolean; className?: string }> = ({
  healthy,
  className,
}) => {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 text-xs",
        healthy ? "text-muted-foreground" : "text-destructive",
        className,
      )}
    >
      {healthy ? (
        <CheckCircle2Icon className="size-3.5" aria-hidden />
      ) : (
        <AlertTriangleIcon className="size-3.5" aria-hidden />
      )}
      {healthy ? "All systems normal" : "Degraded"}
    </span>
  );
};
