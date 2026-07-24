"use client";

import { BlurFade } from "@/components/ui/blur-fade";

interface RevealProps {
  children: React.ReactNode;
  className?: string;
  delay?: number;
  direction?: "up" | "down" | "left" | "right";
  offset?: number;
  blur?: string;
  duration?: number;
  inView?: boolean;
}

export function Reveal({
  children,
  className,
  delay = 0,
  direction = "up",
  offset = 14,
  blur = "6px",
  duration = 0.6,
  inView = true,
}: RevealProps) {
  return (
    <BlurFade
      className={className}
      delay={delay}
      direction={direction}
      offset={offset}
      blur={blur}
      duration={duration}
      inView={inView}
    >
      {children}
    </BlurFade>
  );
}
