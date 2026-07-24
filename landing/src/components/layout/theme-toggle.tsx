"use client";

import {
  AnimatedThemeToggle,
  type TransitionVariant,
} from "@/components/ui/animated-theme-toggle";

export type { TransitionVariant };

export function ThemeToggle({
  variant = "circle",
  fromCenter = false,
  duration = 400,
  className,
}: {
  variant?: TransitionVariant;
  fromCenter?: boolean;
  duration?: number;
  className?: string;
} = {}) {
  return (
    <AnimatedThemeToggle
      variant={variant}
      fromCenter={fromCenter}
      duration={duration}
      className={className}
    />
  );
}
