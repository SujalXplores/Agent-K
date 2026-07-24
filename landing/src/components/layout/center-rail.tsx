import { cn } from "@/lib/utils";

interface CenterRailProps {
  children: React.ReactNode;
  className?: string;
}

export function CenterRail({ children, className }: CenterRailProps) {
  return (
    <div
      className={cn(
        "border-border/60 relative mx-auto flex w-full max-w-(--container-max) flex-1 flex-col border-x",
        className
      )}
    >
      <div
        aria-hidden="true"
        className="bg-border/40 pointer-events-none absolute inset-y-0 left-(--rail-inset) z-0 hidden w-px lg:block"
      />
      <div
        aria-hidden="true"
        className="bg-border/40 pointer-events-none absolute inset-y-0 right-(--rail-inset) z-0 hidden w-px lg:block"
      />
      {children}
    </div>
  );
}
