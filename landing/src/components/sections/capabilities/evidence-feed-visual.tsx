import { Link2 } from "lucide-react";

import { AnimatedList } from "@/components/ui/animated-list";
import { content } from "@/lib/config/content";
import { cn } from "@/lib/utils";

const FEED_META: Record<string, { label: string; dot: string }> = {
  trace: { label: "trace", dot: "bg-law-1" },
  deployment: { label: "deploy", dot: "bg-chart-5" },
  metric: { label: "metric", dot: "bg-law-3" },
  log: { label: "log", dot: "bg-muted-foreground" },
};

function FeedCard({ item }: { item: { kind: string; text: string } }) {
  const meta = FEED_META[item.kind] ?? FEED_META.log;
  return (
    <div className="border-border bg-background/70 flex w-full items-center gap-3 rounded-lg border px-3 py-2.5 shadow-sm">
      <span className="text-muted-foreground inline-flex shrink-0 items-center gap-1.5 font-mono text-[10px] tracking-wide uppercase">
        <span className={cn("size-1.5 rounded-full", meta.dot)} />
        {meta.label}
      </span>
      <span className="text-foreground/80 min-w-0 flex-1 truncate text-xs">
        {item.text}
      </span>
      <Link2 className="text-muted-foreground size-3.5 shrink-0" />
    </div>
  );
}

export function EvidenceFeedVisual() {
  const items = content.capabilities.evidenceFeed;

  return (
    <AnimatedList delay={900} className="w-full">
      {items.map((item, i) => (
        <FeedCard key={i} item={item} />
      ))}
    </AnimatedList>
  );
}
