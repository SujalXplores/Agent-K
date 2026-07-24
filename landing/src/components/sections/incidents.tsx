import { Section } from "@/components/layout/section";
import { SectionHeading } from "@/components/layout/section-heading";
import { Reveal } from "@/components/motion/reveal";
import { IncidentTabs } from "@/components/sections/incident-tabs";
import { content } from "@/lib/config/content";

export function Incidents() {
  return (
    <Section id="incidents" aria-labelledby="incidents-heading">
      <Reveal>
        <SectionHeading id="incidents-heading" {...content.incidents.heading} />
      </Reveal>
      <Reveal delay={0.1} className="mt-12">
        <IncidentTabs />
      </Reveal>
      <Reveal delay={0.15} className="mt-8">
        <p className="mx-auto max-w-2xl text-center text-sm text-muted-foreground">
          {content.incidents.honesty}
        </p>
      </Reveal>
    </Section>
  );
}
