import { Section } from "@/components/layout/section";
import { SectionHeading } from "@/components/layout/section-heading";
import { Reveal } from "@/components/motion/reveal";
import { FaqAccordion } from "@/components/sections/faq-accordion";
import { content } from "@/lib/config/content";

export function Faq() {
  return (
    <Section id="faq" aria-labelledby="faq-heading">
      <Reveal>
        <SectionHeading id="faq-heading" {...content.faq.heading} />
      </Reveal>
      <Reveal delay={0.1} className="mt-12">
        <FaqAccordion />
      </Reveal>
    </Section>
  );
}
