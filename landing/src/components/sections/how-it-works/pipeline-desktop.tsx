"use client";

import { useRef, useState } from "react";
import {
  AnimatePresence,
  motion,
  useMotionValueEvent,
  useScroll,
} from "motion/react";
import { Check } from "lucide-react";

import { BorderBeam } from "@/components/ui/border-beam";
import { usePrefersReducedMotion } from "@/hooks/use-prefers-reduced-motion";
import { cn } from "@/lib/utils";
import {
  PHASE_HEX,
  PHASE_STYLES,
  pad,
  phaseOf,
  steps,
} from "@/components/sections/how-it-works/constants";

export function PipelineDesktop() {
  const prefersReduced = usePrefersReducedMotion();
  const trackRef = useRef<HTMLDivElement>(null);
  const [active, setActive] = useState(0);

  const { scrollYProgress } = useScroll({
    target: trackRef,
    offset: ["start start", "end end"],
  });

  useMotionValueEvent(scrollYProgress, "change", (v) => {
    const idx = Math.round(v * (steps.length - 1));
    setActive(Math.min(steps.length - 1, Math.max(0, idx)));
  });

  const scrollToStep = (i: number) => {
    const track = trackRef.current;
    if (!track) return;
    const absoluteTop = track.getBoundingClientRect().top + window.scrollY;
    const scrollable = track.offsetHeight - window.innerHeight;
    const target = absoluteTop + (i / (steps.length - 1)) * scrollable;
    window.scrollTo({
      top: target,
      behavior: prefersReduced ? "auto" : "smooth",
    });
  };

  const activeStep = steps[active];
  const phase = phaseOf(activeStep.index);
  const styles = PHASE_STYLES[phase.key];
  const PhaseIcon = phase.Icon;

  return (
    <div ref={trackRef} className="relative h-[240vh]">
      <div className="sticky top-0 flex h-screen items-center">
        <div className="grid w-full items-center gap-10 lg:grid-cols-[19rem_minmax(0,1fr)]">
          <ol className="relative flex flex-col gap-0.5">
            <span
              aria-hidden="true"
              className="bg-border absolute top-5 bottom-5 left-6 w-px overflow-hidden"
            >
              <motion.span
                className="from-law-1 via-law-2 to-law-3 block h-full w-full origin-top bg-linear-to-b"
                style={{ scaleY: scrollYProgress }}
              />
            </span>

            {steps.map((step, i) => {
              const s = PHASE_STYLES[phaseOf(step.index).key];
              const isActive = i === active;
              const isDone = i < active;
              return (
                <li key={step.index} className="relative z-10">
                  <button
                    type="button"
                    onClick={() => scrollToStep(i)}
                    aria-current={isActive ? "step" : undefined}
                    className={cn(
                      "flex w-full cursor-pointer items-center gap-3 rounded-lg px-2 py-1.5 text-left transition-colors",
                      isActive ? "bg-accent/60" : "hover:bg-accent/30"
                    )}
                  >
                    <span
                      className={cn(
                        "flex size-8 shrink-0 items-center justify-center rounded-full border font-mono text-xs font-semibold transition-all duration-300",
                        isActive &&
                          cn(
                            s.soft,
                            s.border,
                            s.text,
                            "scale-110 ring-4",
                            s.ring
                          ),
                        isDone && cn(s.dot, "border-transparent text-white"),
                        !isActive &&
                          !isDone &&
                          "border-border bg-background text-muted-foreground"
                      )}
                    >
                      {isDone ? <Check className="size-4" /> : pad(step.index)}
                    </span>
                    <span
                      className={cn(
                        "text-sm font-medium transition-colors",
                        isActive ? "text-foreground" : "text-muted-foreground"
                      )}
                    >
                      {step.title}
                    </span>
                  </button>
                </li>
              );
            })}
          </ol>

          <div className="border-border bg-card/40 relative overflow-hidden rounded-2xl border p-8 lg:min-h-76">
            <div
              aria-hidden="true"
              className={cn(
                "pointer-events-none absolute -top-24 -right-24 size-56 rounded-full opacity-25 blur-3xl transition-colors duration-500",
                styles.dot
              )}
            />
            <AnimatePresence mode="wait">
              <motion.div
                key={active}
                initial={
                  prefersReduced ? { opacity: 0 } : { opacity: 0, y: 10 }
                }
                animate={{ opacity: 1, y: 0 }}
                exit={prefersReduced ? { opacity: 0 } : { opacity: 0, y: -10 }}
                transition={{ duration: 0.3, ease: "easeOut" }}
                className="relative flex flex-col gap-4"
              >
                <span
                  className={cn(
                    "inline-flex w-fit items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium",
                    styles.soft,
                    styles.border,
                    styles.text
                  )}
                >
                  <PhaseIcon className="size-3.5" />
                  {phase.name}
                </span>
                <div className="flex items-baseline gap-2 font-mono">
                  <span
                    className={cn(
                      "text-5xl font-semibold tracking-tighter",
                      styles.text
                    )}
                  >
                    {pad(activeStep.index)}
                  </span>
                  <span className="text-muted-foreground text-sm">
                    / {pad(steps.length)}
                  </span>
                </div>
                <h3 className="text-2xl font-medium tracking-tight">
                  {activeStep.title}
                </h3>
                <p className="text-muted-foreground max-w-md leading-relaxed text-pretty">
                  {activeStep.description}
                </p>
              </motion.div>
            </AnimatePresence>

            <div className="mt-8 flex items-center gap-1.5">
              {steps.map((step, i) => (
                <span
                  key={step.index}
                  className={cn(
                    "h-1 flex-1 rounded-full transition-colors",
                    i === active
                      ? styles.dot
                      : i < active
                        ? "bg-foreground/25"
                        : "bg-border"
                  )}
                />
              ))}
            </div>

            {prefersReduced ? null : (
              <BorderBeam
                key={phase.key}
                colorFrom={PHASE_HEX[phase.key]}
                colorTo={PHASE_HEX[phase.key]}
                size={120}
                duration={8}
                borderWidth={1.5}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
