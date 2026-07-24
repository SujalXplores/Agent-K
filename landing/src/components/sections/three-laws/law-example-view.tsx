import { Check, ShieldCheck, ShieldX, X } from "lucide-react";

import type { LawExample } from "@/lib/config/content";
import { cn } from "@/lib/utils";
import type { LawStyle } from "@/components/sections/three-laws/law-styles";

export function LawExampleView({
  example,
  styles,
}: {
  example: LawExample;
  styles: LawStyle;
}) {
  if (example.kind === "evidence") {
    return (
      <div
        className={cn(
          "rounded-lg border p-4 font-mono text-xs",
          styles.softBorder,
          styles.softBg
        )}
      >
        <div className="flex items-center justify-between gap-2">
          <span className="text-muted-foreground">claim</span>
          <span className={cn("rounded px-1.5 py-0.5", styles.badge)}>
            confidence {example.confidence}
          </span>
        </div>
        <p className="text-foreground/90 mt-2 leading-relaxed">
          &ldquo;{example.claim}&rdquo;
        </p>
        <div className="mt-3 flex flex-col gap-1.5">
          {example.evidence.map((item) => (
            <div key={item.type} className="flex items-center gap-2">
              <span className={cn("shrink-0 font-semibold", styles.text)}>
                {item.type}
              </span>
              <span className="text-muted-foreground min-w-0 truncate">
                {item.query}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (example.kind === "policy") {
    return (
      <div className="flex flex-col gap-3">
        <div
          className={cn(
            "rounded-lg border p-3",
            styles.softBorder,
            styles.softBg
          )}
        >
          <p
            className={cn(
              "flex items-center gap-1.5 text-xs font-semibold",
              styles.text
            )}
          >
            <ShieldCheck className="size-3.5" />
            {example.allow.title}
          </p>
          <ul className="mt-2 flex flex-col gap-1">
            {example.allow.lines.map((line) => (
              <li
                key={line}
                className="text-muted-foreground flex items-start gap-1.5 text-[11px]"
              >
                <Check className={cn("mt-0.5 size-3 shrink-0", styles.check)} />
                {line}
              </li>
            ))}
          </ul>
        </div>
        <div className="border-destructive/25 bg-destructive/5 rounded-lg border p-3">
          <p className="text-destructive flex items-center gap-1.5 text-xs font-semibold">
            <ShieldX className="size-3.5" />
            {example.deny.title}
          </p>
          <ul className="mt-2 flex flex-col gap-1">
            {example.deny.lines.map((line) => (
              <li
                key={line}
                className="text-muted-foreground flex items-start gap-1.5 text-[11px]"
              >
                <X className="text-destructive mt-0.5 size-3 shrink-0" />
                {line}
              </li>
            ))}
          </ul>
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn("rounded-lg border p-4", styles.softBorder, styles.softBg)}
    >
      <div className="grid grid-cols-2 gap-3">
        {example.metrics.map((metric) => (
          <div key={metric.label}>
            <div className="text-foreground font-mono text-sm font-semibold">
              {metric.value}
            </div>
            <div className="text-muted-foreground text-[11px]">
              {metric.label}
            </div>
          </div>
        ))}
      </div>
      <p className="text-muted-foreground mt-3 font-mono text-[10px]">
        {example.note}
      </p>
    </div>
  );
}
