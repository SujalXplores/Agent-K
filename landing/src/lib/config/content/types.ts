export interface SectionHeading {
  eyebrow: string;
  title: string;
  description?: string;
}

export interface Cta {
  label: string;
  href: string;
}

export type TerminalLineKind =
  | "prompt"
  | "alert"
  | "query"
  | "evidence"
  | "verdict-allow"
  | "action"
  | "verify"
  | "muted";

export interface TerminalLine {
  kind: TerminalLineKind;
  text: string;
}

export type LawKey = "law-1" | "law-2" | "law-3";

export type LawExample =
  | {
    kind: "evidence";
    claim: string;
    confidence: number;
    evidence: { type: string; query: string }[];
  }
  | {
    kind: "policy";
    allow: { title: string; lines: string[] };
    deny: { title: string; lines: string[] };
  }
  | {
    kind: "telemetry";
    metrics: { label: string; value: string }[];
    note: string;
  };

export interface Law {
  id: LawKey;
  index: number;
  name: string;
  title: string;
  principle: string;
  description: string;
  points: string[];
  example: LawExample;
}

export interface Capability {
  id: string;
  title: string;
  tag: string;
  description: string;
}

export interface PipelineStep {
  index: number;
  title: string;
  description: string;
}

export interface SafetyCard {
  id: string;
  title: string;
  description: string;
  flow?: string[];
  points: string[];
}

export type Verdict = "allow" | "deny";

export interface Incident {
  id: string;
  index: number;
  name: string;
  tag: string;
  symptom: string;
  investigation: string;
  verdict: Verdict;
  verdictReason: string;
  signal: string;
  series: number[];
  threshold?: number;
  deployAt?: number;
  unit?: string;
}

export interface FaqItem {
  question: string;
  answer: string;
}
