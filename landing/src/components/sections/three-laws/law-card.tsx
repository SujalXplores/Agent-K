import { Check } from "lucide-react";

import { MagicCard } from "@/components/ui/magic-card";
import type { Law } from "@/lib/config/content";
import { cn } from "@/lib/utils";
import { LAW_STYLES } from "@/components/sections/three-laws/law-styles";
import { LawExampleView } from "@/components/sections/three-laws/law-example-view";

export function LawCard({ law }: { law: Law }) {
  const styles = LAW_STYLES[law.id];
  const { Icon } = styles;

  return (
    <MagicCard
      className="h-full rounded-2xl"
      gradientFrom={styles.grad}
      gradientTo={styles.grad}
      gradientColor={styles.grad}
      gradientOpacity={0.1}
    >
      <div className="flex h-full flex-col gap-5 p-6 sm:p-7">
        <div className="flex items-center gap-3">
          <span
            className={cn(
              "flex size-10 items-center justify-center rounded-xl",
              styles.badge
            )}
          >
            <Icon className="size-5" />
          </span>
          <div>
            <p
              className={cn(
                "font-mono text-xs tracking-widest uppercase",
                styles.text
              )}
            >
              {law.name}
            </p>
            <h3 className="text-lg font-semibold tracking-tight">
              {law.title}
            </h3>
          </div>
        </div>

        <p className="text-foreground/90 text-[15px] leading-snug font-medium">
          {law.principle}
        </p>

        <ul className="flex flex-col gap-2">
          {law.points.map((point) => (
            <li
              key={point}
              className="text-muted-foreground flex items-start gap-2 text-sm"
            >
              <Check className={cn("mt-0.5 size-4 shrink-0", styles.check)} />
              <span>{point}</span>
            </li>
          ))}
        </ul>

        <div className="mt-auto pt-2">
          <LawExampleView example={law.example} styles={styles} />
        </div>
      </div>
    </MagicCard>
  );
}
