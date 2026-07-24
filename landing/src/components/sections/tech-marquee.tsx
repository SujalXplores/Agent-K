"use client";

import type { CSSProperties } from "react";

import { BrandIcon, brandHex } from "@/components/icons/brand-icons";
import { Marquee } from "@/components/ui/marquee";
import { techStack, type TechItem } from "@/lib/config/tech-stack";
import { cn } from "@/lib/utils";

function TechChip({ tech }: { tech: TechItem }) {
  return (
    <a
      href={tech.href}
      target="_blank"
      rel="noopener noreferrer"
      title={tech.role}
      style={{ "--brand": brandHex[tech.icon] } as CSSProperties}
      className="group/chip flex shrink-0 items-center gap-2.5 rounded-full border border-border bg-card/50 px-4 py-2.5 transition-all hover:bg-card hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/60"
    >
      <BrandIcon
        icon={tech.icon}
        className="size-5 text-muted-foreground grayscale transition-all duration-300 group-hover/chip:text-(--brand) group-hover/chip:grayscale-0"
      />
      <span className="whitespace-nowrap text-sm font-medium text-foreground/80 transition-colors group-hover/chip:text-foreground">
        {tech.name}
      </span>
    </a>
  );
}

export function TechMarquee({ className }: { className?: string }) {
  return (
    <div className={cn("relative", className)}>
      <Marquee pauseOnHover className="[--duration:38s]">
        {techStack.map((tech) => (
          <TechChip key={tech.icon} tech={tech} />
        ))}
      </Marquee>
      <div className="pointer-events-none absolute inset-y-0 left-0 z-10 w-16 bg-linear-to-r from-background to-transparent sm:w-24" />
      <div className="pointer-events-none absolute inset-y-0 right-0 z-10 w-16 bg-linear-to-l from-background to-transparent sm:w-24" />
    </div>
  );
}
