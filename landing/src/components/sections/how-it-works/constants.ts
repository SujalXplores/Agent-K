import { FileText, Search, ShieldCheck } from "lucide-react";

import { content } from "@/lib/config/content";
import { brandColor } from "@/lib/config/theme";

export const steps = content.howItWorks.steps;

export function pad(index: number) {
  return String(index).padStart(2, "0");
}

export type PhaseKey = "investigate" | "act" | "record";

export const PHASES = [
  { key: "investigate" as const, name: "Investigate", min: 1, max: 5, Icon: Search },
  { key: "act" as const, name: "Decide and act", min: 6, max: 8, Icon: ShieldCheck },
  { key: "record" as const, name: "Record", min: 9, max: 10, Icon: FileText },
];

export const PHASE_STYLES: Record<
  PhaseKey,
  { text: string; dot: string; soft: string; border: string; ring: string }
> = {
  investigate: {
    text: "text-law-1",
    dot: "bg-law-1",
    soft: "bg-law-1/10",
    border: "border-law-1/40",
    ring: "ring-law-1/25",
  },
  act: {
    text: "text-law-2",
    dot: "bg-law-2",
    soft: "bg-law-2/10",
    border: "border-law-2/40",
    ring: "ring-law-2/25",
  },
  record: {
    text: "text-law-3",
    dot: "bg-law-3",
    soft: "bg-law-3/10",
    border: "border-law-3/40",
    ring: "ring-law-3/25",
  },
};

export const PHASE_HEX: Record<PhaseKey, string> = {
  investigate: brandColor.law1,
  act: brandColor.law2,
  record: brandColor.law3,
};

export function phaseOf(index: number) {
  return PHASES.find((p) => index >= p.min && index <= p.max) ?? PHASES[0];
}
