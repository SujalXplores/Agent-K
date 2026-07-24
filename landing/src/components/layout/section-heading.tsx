import { cn } from "@/lib/utils";

interface SectionHeadingProps {
  eyebrow: string;
  title: string;
  description?: string;
  id?: string;
  align?: "center" | "left";
  className?: string;
}

export function SectionHeading({
  eyebrow,
  title,
  description,
  id,
  align = "center",
  className,
}: SectionHeadingProps) {
  return (
    <div
      className={cn(
        "flex flex-col gap-4",
        align === "center"
          ? "items-center text-center"
          : "items-start text-left",
        className
      )}
    >
      <span className="text-primary inline-flex items-center gap-2 font-mono text-xs font-medium tracking-[0.18em] uppercase">
        <span aria-hidden="true" className="bg-primary size-1.5 rounded-full" />
        {eyebrow}
      </span>
      <h2
        id={id}
        className="max-w-3xl text-3xl font-medium tracking-tighter text-balance sm:text-4xl md:text-[2.6rem] md:leading-[1.1]"
      >
        {title}
      </h2>
      {description ? (
        <p
          className={cn(
            "text-muted-foreground max-w-2xl text-base leading-relaxed text-pretty sm:text-lg",
            align === "center" && "mx-auto"
          )}
        >
          {description}
        </p>
      ) : null}
    </div>
  );
}
