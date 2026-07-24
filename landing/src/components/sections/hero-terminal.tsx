"use client";

import {
  ArrowRight,
  ChevronRight,
  CircleCheck,
  CornerDownRight,
  Search,
  ShieldCheck,
  Sparkles,
  SquareTerminal,
  TriangleAlert,
  type LucideIcon,
} from "lucide-react";
import { motion } from "motion/react";

import { BorderBeam } from "@/components/ui/border-beam";
import {
  content,
  type TerminalLine,
  type TerminalLineKind,
} from "@/lib/config/content";
import { brandColor } from "@/lib/config/theme";
import { cn } from "@/lib/utils";

const KIND_CLASS: Record<TerminalLineKind, string> = {
  prompt: "text-zinc-400",
  alert: "text-amber-400",
  query: "text-sky-400",
  evidence: "text-zinc-400",
  "verdict-allow": "font-medium text-emerald-400",
  action: "text-zinc-100",
  verify: "font-medium text-emerald-400",
  muted: "text-zinc-400",
};

const KIND_ICON: Record<TerminalLineKind, LucideIcon> = {
  prompt: ChevronRight,
  alert: TriangleAlert,
  query: Search,
  evidence: CornerDownRight,
  "verdict-allow": ShieldCheck,
  action: ArrowRight,
  verify: CircleCheck,
  muted: Sparkles,
};

const STAGGER = 0.45;

function LineRow({ line }: { line: TerminalLine }) {
  const Icon = KIND_ICON[line.kind];
  return (
    <span
      className={cn("flex min-w-0 items-start gap-2.5", KIND_CLASS[line.kind])}
    >
      <Icon aria-hidden="true" className="mt-0.75 size-3.5 shrink-0" />
      <span className="min-w-0 wrap-break-word whitespace-pre-wrap">
        {line.text}
      </span>
    </span>
  );
}

export function HeroTerminal() {
  const lines = content.hero.terminal.lines;

  return (
    <figure
      aria-label={content.hero.terminal.title}
      className="mx-auto w-full max-w-2xl"
    >
      <div className="relative overflow-hidden rounded-xl border border-zinc-800 bg-zinc-950 shadow-2xl ring-1 shadow-black/20 ring-white/5">
        <div className="flex items-center justify-between border-b border-zinc-800 px-4 py-3">
          <div className="flex gap-1.5">
            <span className="size-2.5 rounded-full bg-red-500" />
            <span className="size-2.5 rounded-full bg-yellow-500" />
            <span className="size-2.5 rounded-full bg-green-500" />
          </div>
          <span className="flex items-center gap-1.5 font-mono text-[11px] text-zinc-400">
            <SquareTerminal className="size-3.5" />
            {content.hero.terminal.title}
          </span>
        </div>

        <div className="p-4">
          <div className="grid gap-y-1.5 font-mono text-sm leading-relaxed">
            {lines.map((line, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{
                  delay: index * STAGGER,
                  duration: 0.3,
                  ease: "easeOut",
                }}
              >
                <LineRow line={line} />
              </motion.div>
            ))}
            <motion.span
              aria-hidden="true"
              className="flex"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: lines.length * STAGGER, duration: 0.3 }}
            >
              <span className="inline-block h-4 w-1.75 animate-pulse rounded-[1px] bg-emerald-400/90 motion-reduce:animate-none" />
            </motion.span>
          </div>
        </div>

        <BorderBeam
          colorFrom={brandColor.law1}
          colorTo={brandColor.law3}
          size={140}
          duration={9}
          borderWidth={1.5}
        />
      </div>
    </figure>
  );
}
