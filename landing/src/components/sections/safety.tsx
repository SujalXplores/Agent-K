import { Fragment } from "react";
import { ArrowRight, Check, FileCode2, ShieldCheck } from "lucide-react";

import { Section } from "@/components/layout/section";
import { SectionHeading } from "@/components/layout/section-heading";
import { Reveal } from "@/components/motion/reveal";
import { DotPattern } from "@/components/ui/dot-pattern";
import { GridPattern } from "@/components/ui/grid-pattern";
import {
  content,
  type SafetyCard as SafetyCardType,
} from "@/lib/config/content";
import { cn } from "@/lib/utils";

function flowChipClass(index: number, total: number) {
  if (index === 0) return "border-primary/20 bg-primary/10 text-primary";
  if (index === total - 1)
    return "border-border bg-muted text-muted-foreground";
  return "border-law-2/40 bg-law-2/10 font-mono text-foreground";
}

function SafetyCard({ card, index }: { card: SafetyCardType; index: number }) {
  const isRollback = index === 0;
  const Icon = isRollback ? ShieldCheck : FileCode2;
  const checkClass = isRollback ? "text-law-2" : "text-primary";

  return (
    <div className="border-border bg-card/40 hover:border-primary/30 relative h-full overflow-hidden rounded-2xl border p-6 transition-colors sm:p-8">
      {isRollback ? (
        <DotPattern
          width={18}
          height={18}
          className="text-law-2/25 mask-[radial-gradient(300px_circle_at_top_right,white,transparent)]"
        />
      ) : (
        <GridPattern
          width={32}
          height={32}
          className="stroke-primary/15 mask-[radial-gradient(320px_circle_at_top_right,white,transparent)]"
        />
      )}

      <div className="relative flex h-full flex-col gap-5">
        <div className="flex items-center gap-3">
          <span
            className={cn(
              "flex size-10 items-center justify-center rounded-xl",
              isRollback
                ? "bg-law-2/10 text-law-2"
                : "bg-primary/10 text-primary"
            )}
          >
            <Icon className="size-5" />
          </span>
          <h3 className="text-lg font-semibold tracking-tight">{card.title}</h3>
        </div>

        <p className="text-muted-foreground text-sm leading-relaxed">
          {card.description}
        </p>

        {card.flow ? (
          <div className="border-border bg-background/50 flex flex-wrap items-center gap-2 rounded-xl border p-3">
            {card.flow.map((node, i) => (
              <Fragment key={node}>
                <span
                  className={cn(
                    "rounded-md border px-2 py-1 text-xs font-medium",
                    flowChipClass(i, card.flow!.length)
                  )}
                >
                  {node}
                </span>
                {i < card.flow!.length - 1 ? (
                  <ArrowRight
                    aria-hidden="true"
                    className="text-muted-foreground size-3.5"
                  />
                ) : null}
              </Fragment>
            ))}
          </div>
        ) : null}

        <ul className="mt-auto flex flex-col gap-2.5 pt-1">
          {card.points.map((point) => (
            <li
              key={point}
              className="text-muted-foreground flex items-start gap-2 text-sm"
            >
              <Check className={cn("mt-0.5 size-4 shrink-0", checkClass)} />
              <span>{point}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export function Safety() {
  const { heading, cards } = content.safety;

  return (
    <Section id="safety" aria-labelledby="safety-heading">
      <Reveal>
        <SectionHeading id="safety-heading" {...heading} />
      </Reveal>
      <div className="mt-12 grid grid-cols-1 gap-5 md:grid-cols-2">
        {cards.map((card, index) => (
          <Reveal key={card.id} delay={index * 0.1} className="h-full">
            <SafetyCard card={card} index={index} />
          </Reveal>
        ))}
      </div>
    </Section>
  );
}
