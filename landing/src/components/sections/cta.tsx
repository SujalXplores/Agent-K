import { ArrowRight } from "lucide-react";

import { GitHubIcon } from "@/components/icons/github";
import { Section } from "@/components/layout/section";
import { Reveal } from "@/components/motion/reveal";
import { DemoDialog } from "@/components/sections/demo-dialog";
import { DotPattern } from "@/components/ui/dot-pattern";
import { ShimmerLink } from "@/components/ui/shimmer-button";
import { content } from "@/lib/config/content";
import { cn } from "@/lib/utils";

export function Cta() {
  const { cta } = content;

  return (
    <Section
      id="cta"
      aria-labelledby="cta-heading"
      className="relative overflow-hidden py-24 sm:py-28 lg:py-32"
    >
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 overflow-hidden"
      >
        <div className="bg-primary/15 absolute top-1/2 left-1/2 size-130 -translate-x-1/2 -translate-y-1/2 rounded-full blur-[110px]" />
        <DotPattern
          width={26}
          height={26}
          className={cn(
            "text-foreground/10",
            "mask-[radial-gradient(600px_circle_at_center,white,transparent_70%)]"
          )}
        />
      </div>

      <div className="relative z-10 mx-auto flex max-w-2xl flex-col items-center gap-6 text-center">
        <Reveal>
          <span className="text-primary inline-flex items-center gap-2 font-mono text-xs font-medium tracking-[0.18em] uppercase">
            <span
              aria-hidden="true"
              className="bg-primary size-1.5 rounded-full"
            />
            {cta.eyebrow}
          </span>
        </Reveal>

        <Reveal delay={0.05}>
          <h2
            id="cta-heading"
            className="text-3xl font-semibold tracking-tight text-balance sm:text-4xl md:text-[2.6rem] md:leading-[1.1]"
          >
            {cta.headline}{" "}
            <span className="text-primary">{cta.headlineEmphasis}</span>
          </h2>
        </Reveal>

        <Reveal delay={0.1}>
          <p className="text-muted-foreground max-w-xl text-base text-pretty sm:text-lg">
            {cta.subhead}
          </p>
        </Reveal>

        <Reveal delay={0.15}>
          <div className="flex flex-col items-center gap-3 sm:flex-row">
            <ShimmerLink
              href={cta.primary.href}
              target="_blank"
              rel="noopener noreferrer"
              background="#0b1020"
              className="h-12 gap-2 text-sm font-medium"
            >
              <GitHubIcon className="size-4" />
              {cta.primary.label}
            </ShimmerLink>
            <DemoDialog triggerClassName="h-12" />
          </div>
        </Reveal>

        <Reveal delay={0.2}>
          <a
            href={cta.blog.href}
            target="_blank"
            rel="noopener noreferrer"
            className="text-muted-foreground hover:text-foreground inline-flex items-center gap-1.5 text-sm transition-colors"
          >
            {cta.blog.label}
            <ArrowRight className="size-3.5" />
          </a>
        </Reveal>
      </div>
    </Section>
  );
}
