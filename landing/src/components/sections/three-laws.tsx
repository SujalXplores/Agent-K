import { Section } from "@/components/layout/section";
import { SectionHeading } from "@/components/layout/section-heading";
import { Reveal } from "@/components/motion/reveal";
import { content } from "@/lib/config/content";
import { LawCard } from "@/components/sections/three-laws/law-card";

export function ThreeLaws() {
  const { heading, items } = content.laws;

  return (
    <Section id="laws" aria-labelledby="laws-heading">
      <Reveal>
        <SectionHeading id="laws-heading" {...heading} />
      </Reveal>
      <div className="mt-12 grid grid-cols-1 gap-5 lg:grid-cols-3">
        {items.map((law, index) => (
          <Reveal key={law.id} delay={index * 0.1} className="h-full">
            <LawCard law={law} />
          </Reveal>
        ))}
      </div>
    </Section>
  );
}
