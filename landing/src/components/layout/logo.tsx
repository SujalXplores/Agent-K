import { cn } from "@/lib/utils";

interface LogoProps {
  className?: string;
  showWordmark?: boolean;
}

export function Logo({ className, showWordmark = true }: LogoProps) {
  return (
    <span className={cn("flex items-center gap-2.5", className)}>
      <svg
        viewBox="0 0 28 28"
        className="size-7 shrink-0"
        role="img"
        aria-label="Agent K"
      >
        <rect width="28" height="28" rx="8" className="fill-primary" />
        <path
          d="M10 7.5v13M18.5 7.5 11 14M12.4 13.2 18.7 20.5"
          fill="none"
          stroke="#ffffff"
          strokeWidth="2.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      {showWordmark ? (
        <span className="text-foreground text-base font-semibold tracking-tight">
          Agent K
        </span>
      ) : null}
    </span>
  );
}
