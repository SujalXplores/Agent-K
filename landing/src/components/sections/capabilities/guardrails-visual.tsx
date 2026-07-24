import { Gauge, Repeat, ShieldCheck } from "lucide-react";

import { content } from "@/lib/config/content";

export function GuardrailsVisual() {
  const guardrails = content.capabilities.guardrails;

  return (
    <div className="flex w-full flex-col gap-3">
      {guardrails.map((guardrail) => {
        const Icon = guardrail.label === "Loop breaker" ? Repeat : Gauge;
        return (
          <div
            key={guardrail.label}
            className="border-border bg-background/60 flex items-center gap-3 rounded-lg border px-3 py-3"
          >
            <span className="bg-law-3/10 text-law-3 flex size-9 items-center justify-center rounded-md">
              <Icon className="size-4" />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium">{guardrail.label}</p>
              <p className="text-muted-foreground text-xs">
                {guardrail.detail}
              </p>
            </div>
            <ShieldCheck className="text-law-2 size-4 shrink-0" />
          </div>
        );
      })}
    </div>
  );
}
