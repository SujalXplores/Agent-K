import { CenterRail } from "@/components/layout/center-rail";
import { Footer } from "@/components/layout/footer";
import { Navbar } from "@/components/layout/navbar";
import { ScrollProgress } from "@/components/layout/scroll-progress";
import { Capabilities } from "@/components/sections/capabilities";
import { Cta } from "@/components/sections/cta";
import { Faq } from "@/components/sections/faq";
import { Hero } from "@/components/sections/hero";
import { HowItWorks } from "@/components/sections/how-it-works";
import { Incidents } from "@/components/sections/incidents";
import { Safety } from "@/components/sections/safety";
import { TechStack } from "@/components/sections/tech-stack";
import { ThreeLaws } from "@/components/sections/three-laws";

export default function Home() {
  return (
    <>
      <ScrollProgress />
      <CenterRail>
        <Navbar />
        <main
          id="main"
          className="flex flex-1 flex-col divide-y divide-border/60"
        >
          <Hero />
          <TechStack />
          <Capabilities />
          <ThreeLaws />
          <HowItWorks />
          <Safety />
          <Incidents />
          <Faq />
          <Cta />
        </main>
      </CenterRail>
      {/* Footer sits outside the rail so the border-x and guide lines stop at
          the main content, matching the template. */}
      <Footer />
    </>
  );
}
