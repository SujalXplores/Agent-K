import React, {
  type ComponentPropsWithoutRef,
  type CSSProperties,
} from "react";

import { cn } from "@/lib/utils";

interface ShimmerStyleProps {
  shimmerColor?: string;
  shimmerSize?: string;
  borderRadius?: string;
  shimmerDuration?: string;
  background?: string;
}

const SHIMMER_CLASS =
  "group relative z-0 flex cursor-pointer items-center justify-center overflow-hidden [border-radius:var(--radius)] border border-white/10 px-6 py-3 whitespace-nowrap text-white [background:var(--bg)] transform-gpu transition-transform duration-300 ease-in-out active:translate-y-px";

function shimmerStyle({
  shimmerColor = "#ffffff",
  shimmerSize = "0.05em",
  shimmerDuration = "3s",
  borderRadius = "100px",
  background = "rgba(0, 0, 0, 1)",
}: ShimmerStyleProps): CSSProperties {
  return {
    "--spread": "90deg",
    "--shimmer-color": shimmerColor,
    "--radius": borderRadius,
    "--speed": shimmerDuration,
    "--cut": shimmerSize,
    "--bg": background,
  } as CSSProperties;
}

function ShimmerLayers({ children }: { children?: React.ReactNode }) {
  return (
    <>
      <div
        className={cn(
          "-z-30 blur-[2px]",
          "@container-size absolute inset-0 overflow-visible"
        )}
      >
        <div className="animate-shimmer-slide absolute inset-0 aspect-[1] h-[100cqh] rounded-none [mask:none]">
          <div className="animate-spin-around absolute -inset-full w-auto [translate:0_0] rotate-0 [background:conic-gradient(from_calc(270deg-(var(--spread)*0.5)),transparent_0,var(--shimmer-color)_var(--spread),transparent_var(--spread))]" />
        </div>
      </div>
      {children}
      <div className="absolute inset-0 size-full transform-gpu rounded-2xl px-4 py-1.5 text-sm font-medium shadow-[inset_0_-8px_10px_#ffffff1f] transition-all duration-300 ease-in-out group-hover:shadow-[inset_0_-6px_10px_#ffffff3f] group-active:shadow-[inset_0_-10px_10px_#ffffff3f]" />
      <div className="absolute inset-(--cut) -z-20 rounded-lg [background:var(--bg)]" />
    </>
  );
}

export interface ShimmerButtonProps
  extends ComponentPropsWithoutRef<"button">, ShimmerStyleProps {}

export const ShimmerButton = React.forwardRef<
  HTMLButtonElement,
  ShimmerButtonProps
>(
  (
    {
      shimmerColor,
      shimmerSize,
      shimmerDuration,
      borderRadius,
      background,
      className,
      children,
      ...props
    },
    ref
  ) => (
    <button
      ref={ref}
      style={shimmerStyle({
        shimmerColor,
        shimmerSize,
        shimmerDuration,
        borderRadius,
        background,
      })}
      className={cn(SHIMMER_CLASS, className)}
      {...props}
    >
      <ShimmerLayers>{children}</ShimmerLayers>
    </button>
  )
);
ShimmerButton.displayName = "ShimmerButton";

export interface ShimmerLinkProps
  extends ComponentPropsWithoutRef<"a">, ShimmerStyleProps {}

/** Anchor variant of the shimmer button, so CTAs can be real links. */
export const ShimmerLink = React.forwardRef<
  HTMLAnchorElement,
  ShimmerLinkProps
>(
  (
    {
      shimmerColor,
      shimmerSize,
      shimmerDuration,
      borderRadius,
      background,
      className,
      children,
      ...props
    },
    ref
  ) => (
    <a
      ref={ref}
      style={shimmerStyle({
        shimmerColor,
        shimmerSize,
        shimmerDuration,
        borderRadius,
        background,
      })}
      className={cn(SHIMMER_CLASS, className)}
      {...props}
    >
      <ShimmerLayers>{children}</ShimmerLayers>
    </a>
  )
);
ShimmerLink.displayName = "ShimmerLink";
