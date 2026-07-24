import { Check, X } from "lucide-react";

import type { Incident } from "@/lib/config/content";
import { cn } from "@/lib/utils";

export function VerdictBadge({ verdict }: { verdict: Incident["verdict"] }) {
  const allow = verdict === "allow";
  return (
    <span
      data-verdict={verdict}
      className={cn(
        "text-foreground inline-flex w-fit items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold",
        allow
          ? "border-law-2/40 bg-law-2/10"
          : "border-destructive/40 bg-destructive/10"
      )}
    >
      {allow ? (
        <Check className="text-law-2 size-3.5" />
      ) : (
        <X className="text-destructive size-3.5" />
      )}
      {allow ? "Rollback allowed" : "Rollback denied"}
    </span>
  );
}
