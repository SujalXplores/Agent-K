import type { ElementType, PropsWithChildren } from "react";

export type RevealVariant = "fade" | "up" | "hero" | "panel" | "side";
type RevealElement = "article" | "div" | "footer" | "header" | "li";

type RevealProps = PropsWithChildren<{
  as?: RevealElement;
  className?: string | undefined;
  delay?: number;
  amount?: number;
  ariaHidden?: boolean;
  variant?: RevealVariant;
}>;

export function Reveal({
  as = "div",
  children,
  className,
  delay = 0,
  amount = 0.12,
  ariaHidden,
  variant = "up",
}: RevealProps) {
  const Component: ElementType = as;

  return (
    <Component
      aria-hidden={ariaHidden}
      className={`content-reveal${className ? ` ${className}` : ""}`}
      data-reveal-delay={delay || undefined}
      data-reveal-state="pending"
      data-reveal-threshold={amount}
      data-reveal-variant={variant}
    >
      {children}
    </Component>
  );
}
