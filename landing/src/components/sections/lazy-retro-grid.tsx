"use client";

import dynamic from "next/dynamic";

const RetroGrid = dynamic(
  () => import("@/components/ui/retro-grid").then((m) => m.RetroGrid),
  { ssr: false }
);

export function LazyRetroGrid({
  opacity,
  className,
}: {
  opacity?: number;
  className?: string;
}) {
  return <RetroGrid opacity={opacity} className={className} />;
}
