"use client";

import { useRef } from "react";

import { BrandIcon } from "@/components/icons/brand-icons";
import { Logo } from "@/components/layout/logo";
import { AnimatedBeam } from "@/components/ui/animated-beam";
import { content } from "@/lib/config/content";
import { brandColor } from "@/lib/config/theme";

function BeamNode({
  label,
  children,
  nodeRef,
}: {
  label: string;
  children: React.ReactNode;
  nodeRef: React.RefObject<HTMLDivElement | null>;
}) {
  return (
    <div className="relative flex shrink-0 flex-col items-center">
      <div
        ref={nodeRef}
        className="border-border bg-background z-10 flex size-12 items-center justify-center rounded-full border shadow-sm"
      >
        {children}
      </div>
      <span className="text-muted-foreground absolute top-[calc(100%+0.4rem)] font-mono text-[11px] whitespace-nowrap">
        {label}
      </span>
    </div>
  );
}

export function InvestigateBeamVisual() {
  const containerRef = useRef<HTMLDivElement>(null);
  const agentRef = useRef<HTMLDivElement>(null);
  const mcpRef = useRef<HTMLDivElement>(null);
  const signozRef = useRef<HTMLDivElement>(null);
  const [agent, mcp, signoz] = content.capabilities.flow;

  return (
    <div className="flex w-full items-center justify-center py-2">
      <div
        ref={containerRef}
        className="relative flex w-full max-w-sm items-center justify-between pb-7"
      >
        <BeamNode label={agent} nodeRef={agentRef}>
          <Logo showWordmark={false} />
        </BeamNode>
        <span
          aria-hidden="true"
          className="from-law-1/40 to-law-3/40 h-px flex-1 bg-linear-to-r"
        />
        <BeamNode label={mcp} nodeRef={mcpRef}>
          <BrandIcon icon="mcp" className="text-foreground size-6" />
        </BeamNode>
        <span
          aria-hidden="true"
          className="from-law-3/40 to-law-2/40 h-px flex-1 bg-linear-to-r"
        />
        <BeamNode label={signoz} nodeRef={signozRef}>
          <BrandIcon icon="signoz" className="text-foreground size-6" />
        </BeamNode>

        <AnimatedBeam
          containerRef={containerRef}
          fromRef={agentRef}
          toRef={mcpRef}
          duration={4}
          gradientStartColor={brandColor.law1}
          gradientStopColor={brandColor.law3}
        />
        <AnimatedBeam
          containerRef={containerRef}
          fromRef={mcpRef}
          toRef={signozRef}
          duration={4}
          delay={0.6}
          gradientStartColor={brandColor.law3}
          gradientStopColor={brandColor.law2}
        />
      </div>
    </div>
  );
}
