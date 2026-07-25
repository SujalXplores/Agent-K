"use client";

import {
  AlertTriangleIcon,
  CheckIcon,
  ExternalLinkIcon,
  LoaderIcon,
  ShieldXIcon,
  XIcon,
} from "lucide-react";
import type { FC } from "react";
import type { Investigation } from "@/lib/agentk";
import { POLICY_CHECKS } from "@/lib/console";
import { cn } from "@/lib/utils";

const Stat: FC<{ label: string; value: string; alarming?: boolean }> = ({
  label,
  value,
  alarming,
}) => (
  <div className="border-border/60 rounded-lg border px-3 py-2">
    <div className="text-muted-foreground text-[11px] tracking-wide uppercase">{label}</div>
    <div
      className={cn(
        "mt-0.5 font-mono text-sm",
        alarming ? "text-destructive font-semibold" : "text-foreground",
      )}
    >
      {value}
    </div>
  </div>
);

/**
 * The six policy checks, with the ones that failed called out.
 *
 * `failed_checks` is the only check-level detail /api/investigations exposes, so
 * a check is shown as passed when it is absent from that list. That is sound for
 * a *decided* investigation but would be misleading before the gate has run — so
 * the whole block is hidden until a verdict exists.
 */
const PolicyChecks: FC<{ failed: string[] }> = ({ failed }) => (
  <div className="grid gap-1.5 sm:grid-cols-2">
    {POLICY_CHECKS.map((check) => {
      const didFail = failed.includes(check.id);
      return (
        <div
          key={check.id}
          className={cn(
            "flex items-center gap-2 rounded-md border px-2.5 py-1.5 text-xs",
            didFail
              ? "border-destructive/40 bg-destructive/5 text-destructive"
              : "border-border/60 text-muted-foreground",
          )}
        >
          {didFail ? (
            <XIcon className="size-3.5 shrink-0" aria-hidden />
          ) : (
            <CheckIcon className="size-3.5 shrink-0 text-emerald-600" aria-hidden />
          )}
          <span>{check.label}</span>
        </div>
      );
    })}
  </div>
);

export const InvestigationPanel: FC<{
  investigation: Investigation | null;
  pending: boolean;
  reportsBase?: string;
}> = ({ investigation, pending, reportsBase }) => {
  if (!investigation) {
    return (
      <div className="border-border/60 text-muted-foreground flex min-h-48 flex-col items-center justify-center gap-2 rounded-xl border border-dashed p-8 text-sm">
        {pending ? (
          <>
            <LoaderIcon className="size-4 animate-spin" aria-hidden />
            Waiting for Agent K to pick up the alert…
          </>
        ) : (
          "Run a scenario to start an investigation."
        )}
      </div>
    );
  }

  const inv = investigation;
  const approved = inv.verdict === "approved";
  const decided = inv.verdict != null;

  return (
    <div className="border-border/60 space-y-5 rounded-xl border p-4 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-semibold">{inv.alertname}</h3>
            {inv.incomplete && (
              <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/15 px-2 py-0.5 text-[11px] font-semibold text-amber-700 dark:text-amber-300">
                <AlertTriangleIcon className="size-3" aria-hidden />
                needs human
              </span>
            )}
          </div>
          <p className="text-muted-foreground mt-0.5 font-mono text-xs">
            {inv.id} · {inv.state}
          </p>
        </div>
        {reportsBase && (
          <a
            href={`${reportsBase.replace(/\/+$/, "")}/${inv.id}`}
            target="_blank"
            rel="noreferrer"
            className="border-border/60 hover:bg-muted inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs transition-colors"
          >
            Full RCA report
            <ExternalLinkIcon className="size-3" aria-hidden />
          </a>
        )}
      </div>

      {/* Law 1 — claims, each with its code-recalibrated confidence. Claims with
          no evidence are already stripped upstream, so an empty list here means
          Law 1 removed everything rather than that nothing was proposed. */}
      <section className="space-y-2">
        <h4 className="text-muted-foreground text-[11px] font-semibold tracking-wide uppercase">
          Law 1 · evidence-backed claims
        </h4>
        {inv.claims.length === 0 ? (
          <p className="text-muted-foreground text-xs">
            No claim survived the evidence check — nothing unevidenced is published.
          </p>
        ) : (
          <ul className="space-y-1.5">
            {inv.claims.map((claim, i) => (
              <li
                key={i}
                className="border-border/60 flex items-start gap-3 rounded-md border px-3 py-2 text-xs"
              >
                <span className="bg-muted shrink-0 rounded px-1.5 py-0.5 font-mono">
                  {claim.confidence.toFixed(2)}
                </span>
                <span>{claim.claim}</span>
              </li>
            ))}
          </ul>
        )}
        {inv.incident_type && (
          <p className="text-muted-foreground text-xs">
            Diagnosed as <span className="text-foreground font-mono">{inv.incident_type}</span>
          </p>
        )}
      </section>

      {/* Law 2 — the gate. Denials are styled as prominently as approvals: a
          denial is the evidence that code, not the model, is deciding. */}
      <section className="space-y-2">
        <h4 className="text-muted-foreground text-[11px] font-semibold tracking-wide uppercase">
          Law 2 · policy gate
        </h4>
        {!decided ? (
          <p className="text-muted-foreground text-xs">Gate has not run yet.</p>
        ) : (
          <>
            <div
              className={cn(
                "flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-semibold",
                approved
                  ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
                  : "border-destructive/40 bg-destructive/10 text-destructive",
              )}
            >
              {approved ? (
                <CheckIcon className="size-4" aria-hidden />
              ) : (
                <ShieldXIcon className="size-4" aria-hidden />
              )}
              rollback {inv.verdict}
              {inv.confidence != null && (
                <span className="ml-auto font-mono text-xs font-normal opacity-80">
                  confidence {inv.confidence.toFixed(2)}
                </span>
              )}
            </div>
            <PolicyChecks failed={inv.failed_checks} />
            {inv.action_status && (
              <p className="text-muted-foreground text-xs">
                Action <span className="text-foreground font-mono">{inv.action_status}</span>
                {inv.action_verified != null && (
                  <>
                    {" · recovery "}
                    <span
                      className={cn(
                        "font-mono",
                        inv.action_verified ? "text-emerald-600" : "text-destructive",
                      )}
                    >
                      {inv.action_verified ? "verified" : "not verified"}
                    </span>
                  </>
                )}
              </p>
            )}
          </>
        )}
      </section>

      {/* Law 3 — the agent's own cost and behaviour. */}
      <section className="space-y-2">
        <h4 className="text-muted-foreground text-[11px] font-semibold tracking-wide uppercase">
          Law 3 · self-telemetry
        </h4>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <Stat label="Tokens" value={inv.total_tokens.toLocaleString()} />
          <Stat
            label="Duration"
            value={inv.duration_s != null ? `${inv.duration_s.toFixed(1)}s` : "—"}
          />
          <Stat label="MCP queries" value={String(inv.mcp_query_count)} />
          <Stat
            label="MCP failures"
            value={String(inv.mcp_query_failures)}
            alarming={inv.mcp_query_failures > 0}
          />
        </div>
        {inv.watchdog_events.length > 0 && (
          <div className="border-destructive/40 bg-destructive/5 space-y-1 rounded-lg border px-3 py-2">
            <div className="text-destructive flex items-center gap-1.5 text-xs font-semibold">
              <AlertTriangleIcon className="size-3.5" aria-hidden />
              Guardrail fired
            </div>
            {inv.watchdog_events.map((event, i) => (
              <pre
                key={i}
                className="text-destructive/90 overflow-x-auto font-mono text-[11px] whitespace-pre-wrap"
              >
                {JSON.stringify(event)}
              </pre>
            ))}
          </div>
        )}
      </section>
    </div>
  );
};
