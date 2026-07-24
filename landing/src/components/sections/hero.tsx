import { GitHubIcon } from "@/components/icons/github";
import { Section } from "@/components/layout/section";
import { Reveal } from "@/components/motion/reveal";
import { DemoDialog } from "@/components/sections/demo-dialog";
import { HeroBadge } from "@/components/sections/hero-badge";
import { HeroHeadline } from "@/components/sections/hero-headline";
import { HeroTerminal } from "@/components/sections/hero-terminal";
import { buttonVariants } from "@/components/ui/button";
import { GridPattern } from "@/components/ui/grid-pattern";
import { content } from "@/lib/config/content";
import { siteConfig } from "@/lib/config/site";
import { cn } from "@/lib/utils";

const RAISED =
  "shadow-[inset_0_1px_0_0_rgb(255_255_255/0.18),0_2px_10px_-2px_rgb(2_6_23/0.35)] transition-transform active:scale-95";

export function Hero() {
  return (
    <Section
      id="hero"
      aria-label="Introduction"
      className="relative overflow-hidden pt-24 sm:pt-28 lg:pt-36"
    >
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 -z-10 overflow-hidden"
      >
        <div className="absolute inset-x-0 top-0 h-155 rounded-b-4xl [background:radial-gradient(125%_125%_at_50%_8%,var(--background)_38%,color-mix(in_oklch,var(--primary)_9%,var(--secondary))_100%)] md:h-205" />
        <GridPattern
          width={46}
          height={46}
          className={cn(
            "stroke-foreground/5 absolute inset-0 h-full w-full fill-none",
            "mask-[radial-gradient(760px_circle_at_50%_-20px,black,transparent_78%)]"
          )}
        />
      </div>

      <div className="mx-auto flex max-w-3xl flex-col items-center gap-8 text-center">
        <Reveal inView={false}>
          <HeroBadge />
        </Reveal>

        <div className="flex flex-col items-center gap-5">
          <Reveal inView={false} delay={0.05}>
            <h1 className="text-4xl leading-[1.04] font-medium tracking-tighter text-balance sm:text-5xl lg:text-6xl">
              <HeroHeadline />
            </h1>
          </Reveal>

          <Reveal inView={false} delay={0.1}>
            <p className="text-muted-foreground max-w-2xl text-lg leading-relaxed font-medium tracking-tight text-pretty sm:text-xl">
              {content.hero.subhead}
            </p>
          </Reveal>
        </div>

        <Reveal inView={false} delay={0.15}>
          <div className="flex flex-col items-center gap-3 sm:flex-row">
            <a
              href={siteConfig.links.github}
              target="_blank"
              rel="noopener noreferrer"
              className={cn(
                buttonVariants({ variant: "default" }),
                "h-11 gap-2 rounded-full border border-white/10 bg-[#0b1020] px-6 text-sm text-white hover:bg-[#0b1020]/90",
                RAISED
              )}
            >
              <GitHubIcon className="size-4" />
              {content.hero.primaryCta.label}
            </a>
            <DemoDialog triggerClassName={RAISED} />
          </div>
        </Reveal>

        <Reveal inView={false} delay={0.2}>
          <p className="text-muted-foreground text-sm">{content.hero.note}</p>
        </Reveal>
      </div>

      <Reveal
        inView={false}
        delay={0.25}
        className="relative mx-auto mt-16 w-full max-w-2xl sm:mt-20"
      >
        <div
          aria-hidden="true"
          className="bg-radial-primary pointer-events-none absolute -inset-x-8 -top-10 -z-10 h-48 opacity-70 blur-2xl"
        />
        <HeroTerminal />
      </Reveal>
    </Section>
  );
}
