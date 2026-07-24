import { hero } from "@/lib/config/content/hero";
import { techStack } from "@/lib/config/content/tech-stack";
import { capabilities } from "@/lib/config/content/capabilities";
import { laws } from "@/lib/config/content/laws";
import { howItWorks } from "@/lib/config/content/how-it-works";
import { safety } from "@/lib/config/content/safety";
import { incidents } from "@/lib/config/content/incidents";
import { faq } from "@/lib/config/content/faq";
import { cta } from "@/lib/config/content/cta";
import { footer } from "@/lib/config/content/footer";

export type {
  SectionHeading,
  Cta,
  TerminalLine,
  TerminalLineKind,
  LawKey,
  LawExample,
  Law,
  Capability,
  PipelineStep,
  SafetyCard,
  Verdict,
  Incident,
  FaqItem,
} from "@/lib/config/content/types";

export const content = {
  hero,
  techStack,
  capabilities,
  laws,
  howItWorks,
  safety,
  incidents,
  faq,
  cta,
  footer,
} as const;

export type Content = typeof content;