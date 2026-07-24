"use client";

import { AnimatedShinyText } from "@/components/ui/animated-shiny-text";
import { usePrefersReducedMotion } from "@/hooks/use-prefers-reduced-motion";
import { content } from "@/lib/config/content";
import { cn } from "@/lib/utils";

export function HeroBadge({ className }: { className?: string }) {
  const prefersReduced = usePrefersReducedMotion();

  return (
    <div
      className={cn(
        "inline-flex items-center gap-2 rounded-full border border-border bg-background/60 px-4 py-1.5 text-sm shadow-sm backdrop-blur",
        className
      )}
    >
      <span aria-hidden="true" className="size-1.5 rounded-full bg-primary" />
      {prefersReduced ? (
        <span className="text-muted-foreground">{content.hero.badge}</span>
      ) : (
        <AnimatedShinyText className="text-muted-foreground">
          {content.hero.badge}
        </AnimatedShinyText>
      )}
    </div>
  );
}
