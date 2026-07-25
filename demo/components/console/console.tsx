"use client";

import { ExternalLinkIcon, LoaderIcon, PlayIcon, RotateCcwIcon } from "lucide-react";
import { type FC, useCallback, useEffect, useRef, useState } from "react";
import { InvestigationPanel } from "@/components/console/investigation-panel";
import { FlowdeckLogo } from "@/components/flowdeck/logo";
import { Button } from "@/components/ui/button";
import type { Investigation } from "@/lib/agentk";
import { GUARDRAIL_SPECS, SCENARIO_SPECS } from "@/lib/console";
import { cn } from "@/lib/utils";

type Links = { reports?: string; dashboard?: string };

const POLL_MS = 2000;
/**
 * How long to keep polling for a new investigation before giving up.
 *
 * Generous because a real investigation makes several LLM calls; the recorded
 * eval runs ranged roughly 1-7s, but a cold provider or a rate-limit retry can
 * be much slower, and a demo that gave up early would look like a failure when
 * it was only slow.
 */
const POLL_TIMEOUT_MS = 120_000;

export const Console: FC<{ links: Links }> = ({ links }) => {
  const [investigations, setInvestigations] = useState<Investigation[] | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [running, setRunning] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [awaitingNew, setAwaitingNew] = useState(false);

  // Ids known before the current run started, so the newly-created
  // investigation can be told apart from history without relying on ordering.
  const knownIds = useRef<Set<string>>(new Set());
  const deadline = useRef<number>(0);

  const refresh = useCallback(async (signal?: AbortSignal) => {
    const response = await fetch("/api/investigations", { signal, cache: "no-store" });
    const { investigations: list } = (await response.json()) as {
      investigations: Investigation[] | null;
    };
    if (list == null) return null;
    setInvestigations(list);
    return list;
  }, []);

  // Poll while a run is in flight, and select the new investigation as soon as
  // one appears. Stops polling once nothing is pending, so an idle console is
  // not hammering the app during a demo.
  useEffect(() => {
    if (!awaitingNew) return;

    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;
    let cancelled = false;

    const tick = async () => {
      try {
        const list = await refresh(controller.signal);
        if (cancelled) return;

        const fresh = list?.find((i) => !knownIds.current.has(i.id));
        if (fresh) {
          setSelectedId(fresh.id);
          // Keep polling briefly: the record appears as soon as the
          // investigation starts, so verdict/claims/tokens arrive after it.
          if (fresh.verdict != null || fresh.incomplete) {
            setAwaitingNew(false);
            return;
          }
        }
        if (Date.now() > deadline.current) {
          setAwaitingNew(false);
          setError("Timed out waiting for Agent K. Check the rag-app logs.");
          return;
        }
      } catch {
        if (cancelled) return;
      }
      if (!cancelled) timer = setTimeout(tick, POLL_MS);
    };

    void tick();
    return () => {
      cancelled = true;
      controller.abort();
      if (timer) clearTimeout(timer);
    };
  }, [awaitingNew, refresh]);

  // One initial load so history is visible before anything is run.
  useEffect(() => {
    const controller = new AbortController();
    void refresh(controller.signal).catch(() => {});
    return () => controller.abort();
  }, [refresh]);

  const runScenario = async (scenario: string) => {
    setRunning(scenario);
    setError(null);
    try {
      const response = await fetch("/api/scenario", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scenario }),
      });
      const data = (await response.json()) as { knownIds?: string[]; error?: string };
      if (!response.ok) throw new Error(data.error ?? "scenario failed");

      knownIds.current = new Set(data.knownIds ?? []);
      deadline.current = Date.now() + POLL_TIMEOUT_MS;
      setSelectedId(null);
      setAwaitingNew(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "scenario failed");
    } finally {
      setRunning(null);
    }
  };

  const reset = async () => {
    setError(null);
    try {
      const response = await fetch("/api/scenario", { method: "DELETE" });
      if (!response.ok) {
        const data = (await response.json()) as { error?: string };
        throw new Error(data.error ?? "could not clear scenarios");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "could not clear scenarios");
    }
  };

  const selected =
    investigations?.find((i) => i.id === selectedId) ??
    (selectedId == null ? (investigations?.[0] ?? null) : null);

  return (
    <div className="mx-auto max-w-5xl space-y-8 px-4 py-8">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <FlowdeckLogo className="text-foreground size-6" />
          <div>
            <h1 className="text-lg font-semibold">Agent K · demo console</h1>
            <p className="text-muted-foreground text-xs">
              Break Flowdeck on purpose, then watch the three Laws decide what happens next.
            </p>
          </div>
        </div>
        <nav className="flex flex-wrap items-center gap-3 text-sm">
          <a
            href="/"
            className="text-muted-foreground hover:text-foreground inline-flex items-center gap-1 transition-colors"
          >
            Help centre
          </a>
          {links.reports && (
            <a
              href={links.reports}
              target="_blank"
              rel="noreferrer"
              className="text-muted-foreground hover:text-foreground inline-flex items-center gap-1 transition-colors"
            >
              All reports
              <ExternalLinkIcon className="size-3" aria-hidden />
            </a>
          )}
          {links.dashboard && (
            <a
              href={links.dashboard}
              target="_blank"
              rel="noreferrer"
              className="text-muted-foreground hover:text-foreground inline-flex items-center gap-1 transition-colors"
            >
              SigNoz dashboard
              <ExternalLinkIcon className="size-3" aria-hidden />
            </a>
          )}
        </nav>
      </header>

      {error && (
        <div className="border-destructive/40 bg-destructive/10 text-destructive rounded-lg border px-3 py-2 text-sm">
          {error}
        </div>
      )}

      <section className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="font-semibold">The four incidents</h2>
            <p className="text-muted-foreground text-xs">
              Each click sets the flag, puts real traffic through <code>/ask</code>, and fires the
              alert webhook — the same sequence the eval harness runs.
            </p>
          </div>
          <Button variant="ghost" onClick={reset} className="gap-1.5 text-xs">
            <RotateCcwIcon className="size-3.5" aria-hidden />
            Back to healthy
          </Button>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          {SCENARIO_SPECS.map((spec) => {
            const isRunning = running === spec.id;
            return (
              <div
                key={spec.id}
                className="border-border/60 flex flex-col gap-2 rounded-xl border p-4"
              >
                <div className="flex items-start justify-between gap-2">
                  <h3 className="text-sm font-semibold">{spec.label}</h3>
                  <span
                    className={cn(
                      "shrink-0 rounded-full px-2 py-0.5 text-[11px] font-semibold",
                      spec.expectedVerdict === "approved"
                        ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300"
                        : "bg-destructive/15 text-destructive",
                    )}
                  >
                    expect {spec.expectedVerdict}
                  </span>
                </div>
                <p className="text-muted-foreground text-xs">{spec.blurb}</p>
                <p className="text-muted-foreground/80 text-xs italic">{spec.because}</p>
                <Button
                  onClick={() => runScenario(spec.id)}
                  disabled={running != null || awaitingNew}
                  className="mt-1 w-full gap-1.5 text-xs"
                >
                  {isRunning ? (
                    <LoaderIcon className="size-3.5 animate-spin" aria-hidden />
                  ) : (
                    <PlayIcon className="size-3.5" aria-hidden />
                  )}
                  Run this incident
                </Button>
              </div>
            );
          })}
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="font-semibold">Live investigation</h2>
        <InvestigationPanel
          investigation={selected}
          pending={awaitingNew}
          reportsBase={links.reports}
        />
      </section>

      <section className="space-y-3">
        <div>
          <h2 className="font-semibold">Law 3 guardrails</h2>
          <p className="text-muted-foreground text-xs">
            Both fire on the real code path — the threshold is tightened, the guardrail is not
            bypassed. Set the variable, recreate the app, then run any incident above and watch{" "}
            <span className="font-mono">Guardrail fired</span> appear in the panel.
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          {GUARDRAIL_SPECS.map((spec) => (
            <div key={spec.id} className="border-border/60 space-y-2 rounded-xl border p-4">
              <h3 className="text-sm font-semibold">{spec.label}</h3>
              <p className="text-muted-foreground text-xs">{spec.blurb}</p>
              <pre className="bg-muted/60 overflow-x-auto rounded-md px-2.5 py-2 font-mono text-[11px]">
                {`${spec.envVar}=${spec.demoValue} \\\n  docker compose up -d --force-recreate rag-app`}
              </pre>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
};
