import { cn } from "@/lib/utils";

interface SectionProps extends React.HTMLAttributes<HTMLElement> {
  id: string;
}

export function Section({ id, className, children, ...props }: SectionProps) {
  return (
    <section
      id={id}
      className={cn(
        "relative scroll-mt-24 px-6 py-20 sm:py-24 lg:py-28",
        className
      )}
      {...props}
    >
      {children}
    </section>
  );
}
