import { Section } from "@/components/layout/section";
import { SectionHeading } from "@/components/layout/section-heading";
import { Reveal } from "@/components/motion/reveal";
import { TechMarquee } from "@/components/sections/tech-marquee";
import { content } from "@/lib/config/content";

export function TechStack() {
  return (
    <Section id="stack" aria-labelledby="stack-heading" className="py-16 sm:py-20">
      <Reveal>
        <SectionHeading
          id="stack-heading"
          eyebrow={content.techStack.eyebrow}
          title={content.techStack.title}
          description={content.techStack.description}
        />
      </Reveal>
      <Reveal delay={0.1} className="mt-10">
        <TechMarquee />
      </Reveal>
    </Section>
  );
}
