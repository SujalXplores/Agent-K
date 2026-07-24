import { Activity, FileSearch, ShieldCheck } from "lucide-react";

import type { LawKey } from "@/lib/config/content";

export interface LawStyle {
  text: string;
  badge: string;
  check: string;
  softBg: string;
  softBorder: string;
  grad: string;
  Icon: typeof FileSearch;
}

export const LAW_STYLES: Record<LawKey, LawStyle> = {
  "law-1": {
    text: "text-law-1",
    badge: "bg-law-1/10 text-law-1",
    check: "text-law-1",
    softBg: "bg-law-1/5",
    softBorder: "border-law-1/20",
    grad: "var(--law-1)",
    Icon: FileSearch,
  },
  "law-2": {
    text: "text-law-2",
    badge: "bg-law-2/10 text-law-2",
    check: "text-law-2",
    softBg: "bg-law-2/5",
    softBorder: "border-law-2/20",
    grad: "var(--law-2)",
    Icon: ShieldCheck,
  },
  "law-3": {
    text: "text-law-3",
    badge: "bg-law-3/10 text-law-3",
    check: "text-law-3",
    softBg: "bg-law-3/5",
    softBorder: "border-law-3/20",
    grad: "var(--law-3)",
    Icon: Activity,
  },
};
