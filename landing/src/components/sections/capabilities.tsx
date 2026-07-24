import type { ComponentType } from "react";

import { Section } from "@/components/layout/section";
import { SectionHeading } from "@/components/layout/section-heading";
import { Reveal } from "@/components/motion/reveal";
import {
  EvidenceFeedVisual,
  GuardrailsVisual,
  InvestigateBeamVisual,
  TelemetryVisual,
} from "@/components/sections/capability-visuals";
import { content } from "@/lib/config/content";
import { cn } from "@/lib/utils";

const VISUALS: Record<string, ComponentType> = {
  evidence: EvidenceFeedVisual,
  investigate: InvestigateBeamVisual,
  "self-telemetry": TelemetryVisual,
  guardrails: GuardrailsVisual,
};

function BentoTile({
  tag,
  title,
  description,
  children,
  className,
}: {
  tag: string;
  title: string;
  description: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "group border-border bg-card/40 hover:border-primary/30 flex h-full min-h-80 flex-col overflow-hidden rounded-2xl border p-6 transition-colors",
        className
      )}
    >
      <div className="flex flex-1 items-center justify-center">{children}</div>
      <div className="mt-6">
        <p className="text-primary font-mono text-xs tracking-widest uppercase">
          {tag}
        </p>
        <h3 className="mt-2 text-lg font-semibold tracking-tight">{title}</h3>
        <p className="text-muted-foreground mt-1.5 text-sm leading-relaxed">
          {description}
        </p>
      </div>
    </div>
  );
}

export function Capabilities() {
  const { heading, items } = content.capabilities;

  return (
    <Section id="capabilities" aria-labelledby="capabilities-heading">
      <Reveal>
        <SectionHeading id="capabilities-heading" {...heading} />
      </Reveal>
      <div className="mt-12 grid grid-cols-1 gap-4 md:grid-cols-2">
        {items.map((capability, index) => {
          const Visual = VISUALS[capability.id];
          return (
            <Reveal key={capability.id} delay={index * 0.08} className="h-full">
              <BentoTile
                tag={capability.tag}
                title={capability.title}
                description={capability.description}
              >
                {Visual ? <Visual /> : null}
              </BentoTile>
            </Reveal>
          );
        })}
      </div>
    </Section>
  );
}
