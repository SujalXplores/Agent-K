import { Section } from "@/components/layout/section";
import { SectionHeading } from "@/components/layout/section-heading";
import { Reveal } from "@/components/motion/reveal";
import {
  PipelineDesktop,
  StepperMobile,
} from "@/components/sections/how-it-works-flow";
import { content } from "@/lib/config/content";

export function HowItWorks() {
  return (
    <Section id="how-it-works" aria-labelledby="how-it-works-heading">
      <Reveal>
        <SectionHeading
          id="how-it-works-heading"
          {...content.howItWorks.heading}
        />
      </Reveal>
      <div className="mt-12">
        <div className="hidden lg:block">
          <PipelineDesktop />
        </div>
        <div className="lg:hidden">
          <StepperMobile />
        </div>
      </div>
    </Section>
  );
}
