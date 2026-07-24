"use client";

import * as React from "react";
import { Moon, Sun } from "lucide-react";
import { flushSync } from "react-dom";
import { useTheme } from "next-themes";

import { cn } from "@/lib/utils";

export type TransitionVariant =
  | "circle"
  | "square"
  | "triangle"
  | "diamond"
  | "hexagon"
  | "rectangle"
  | "star";

export interface AnimatedThemeToggleProps
  extends React.ComponentPropsWithoutRef<"button"> {
  /** Duration of the theme transition animation in milliseconds. */
  duration?: number;
  /** Shape used for the view-transition clip-path reveal. */
  variant?: TransitionVariant;
  /** When true, the transition expands from the viewport center instead of the button. */
  fromCenter?: boolean;
}

function polygonCollapsed(point: string, vertexCount: number): string {
  const pairs = Array.from({ length: vertexCount }, () => point).join(", ");
  return `polygon(${pairs})`;
}

function getThemeTransitionClipPaths(
  variant: TransitionVariant,
  cx: number,
  cy: number,
  maxRadius: number,
  viewportWidth: number,
  viewportHeight: number
): [string, string] {
  const toX = (x: number) => `${(x / viewportWidth) * 100}%`;
  const toY = (y: number) => `${(y / viewportHeight) * 100}%`;
  const point = (x: number, y: number) => `${toX(x)} ${toY(y)}`;
  // circle() percentage radii resolve against hypot(w, h) / sqrt(2) of the reference box.
  const toRadius = (r: number) =>
    `${(r / (Math.hypot(viewportWidth, viewportHeight) / Math.SQRT2)) * 100}%`;

  switch (variant) {
    case "circle":
      return [
        `circle(0% at ${point(cx, cy)})`,
        `circle(${toRadius(maxRadius)} at ${point(cx, cy)})`,
      ];
    case "square": {
      const halfW = Math.max(cx, viewportWidth - cx);
      const halfH = Math.max(cy, viewportHeight - cy);
      const halfSide = Math.max(halfW, halfH) * 1.05;
      const end = [
        point(cx - halfSide, cy - halfSide),
        point(cx + halfSide, cy - halfSide),
        point(cx + halfSide, cy + halfSide),
        point(cx - halfSide, cy + halfSide),
      ].join(", ");
      return [polygonCollapsed(point(cx, cy), 4), `polygon(${end})`];
    }
    case "triangle": {
      const scale = maxRadius * 2.2;
      const dx = (Math.sqrt(3) / 2) * scale;
      const verts = [
        point(cx, cy - scale),
        point(cx + dx, cy + 0.5 * scale),
        point(cx - dx, cy + 0.5 * scale),
      ].join(", ");
      return [polygonCollapsed(point(cx, cy), 3), `polygon(${verts})`];
    }
    case "diamond": {
      // Slightly larger than the view-transition circle radius so axis-aligned coverage matches the circle reveal.
      const R = maxRadius * Math.SQRT2;
      const end = [
        point(cx, cy - R),
        point(cx + R, cy),
        point(cx, cy + R),
        point(cx - R, cy),
      ].join(", ");
      return [polygonCollapsed(point(cx, cy), 4), `polygon(${end})`];
    }
    case "hexagon": {
      const R = maxRadius * Math.SQRT2;
      const verts: string[] = [];
      for (let i = 0; i < 6; i++) {
        const a = -Math.PI / 2 + (i * Math.PI) / 3;
        verts.push(point(cx + R * Math.cos(a), cy + R * Math.sin(a)));
      }
      return [
        polygonCollapsed(point(cx, cy), 6),
        `polygon(${verts.join(", ")})`,
      ];
    }
    case "rectangle": {
      const halfW = Math.max(cx, viewportWidth - cx);
      const halfH = Math.max(cy, viewportHeight - cy);
      const end = [
        point(cx - halfW, cy - halfH),
        point(cx + halfW, cy - halfH),
        point(cx + halfW, cy + halfH),
        point(cx - halfW, cy + halfH),
      ].join(", ");
      return [polygonCollapsed(point(cx, cy), 4), `polygon(${end})`];
    }
    case "star": {
      // Small overscan so the last frames never leave a 1px seam before the transition group ends.
      const R = maxRadius * Math.SQRT2 * 1.03;
      const innerRatio = 0.42;
      const starPolygon = (radius: number) => {
        const verts: string[] = [];
        for (let i = 0; i < 5; i++) {
          const outerA = -Math.PI / 2 + (i * 2 * Math.PI) / 5;
          verts.push(
            point(
              cx + radius * Math.cos(outerA),
              cy + radius * Math.sin(outerA)
            )
          );
          const innerA = outerA + Math.PI / 5;
          verts.push(
            point(
              cx + radius * innerRatio * Math.cos(innerA),
              cy + radius * innerRatio * Math.sin(innerA)
            )
          );
        }
        return `polygon(${verts.join(", ")})`;
      };
      const startR = Math.max(2, R * 0.025);
      return [starPolygon(startR), starPolygon(R)];
    }
    default:
      return [
        `circle(0% at ${point(cx, cy)})`,
        `circle(${toRadius(maxRadius)} at ${point(cx, cy)})`,
      ];
  }
}

export const AnimatedThemeToggle = React.forwardRef<
  HTMLButtonElement,
  AnimatedThemeToggleProps
>(
  (
    {
      className,
      duration = 400,
      variant,
      fromCenter = false,
      ...props
    },
    forwardedRef
  ) => {
    const shape = variant ?? "circle";
    const { resolvedTheme, setTheme } = useTheme();
    const isDark = resolvedTheme === "dark";

    const buttonRef = React.useRef<HTMLButtonElement>(null);
    const isTransitioningRef = React.useRef(false);

    React.useImperativeHandle(forwardedRef, () => buttonRef.current as HTMLButtonElement);

    const toggleTheme = React.useCallback(() => {
      const button = buttonRef.current;
      if (
        !button ||
        isTransitioningRef.current ||
        document.documentElement.dataset.magicuiThemeVt === "active"
      )
        return;

      // innerWidth/innerHeight (not visualViewport): percentages must resolve
      // against the snapshot reference box, which includes classic scrollbars.
      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;

      let x: number;
      let y: number;
      if (fromCenter) {
        x = viewportWidth / 2;
        y = viewportHeight / 2;
      } else {
        const { top, left, width, height } = button.getBoundingClientRect();
        x = left + width / 2;
        y = top + height / 2;
      }

      const maxRadius = Math.hypot(
        Math.max(x, viewportWidth - x),
        Math.max(y, viewportHeight - y)
      );

      const applyTheme = () => {
        // next-themes owns persistence; just flip it and let subscribers sync.
        setTheme(isDark ? "light" : "dark");
      };

      if (typeof document.startViewTransition !== "function") {
        applyTheme();
        return;
      }

      const clipPath = getThemeTransitionClipPaths(
        shape,
        x,
        y,
        maxRadius,
        viewportWidth,
        viewportHeight
      );

      const root = document.documentElement;
      root.dataset.magicuiThemeVt = "active";
      root.style.setProperty(
        "--magicui-theme-toggle-vt-duration",
        `${duration}ms`
      );
      // Pin the collapsed clip-path via CSS so Firefox does not paint the new
      // theme unclipped between snapshot and the ready.then() JS animation.
      root.style.setProperty("--magicui-theme-vt-clip-from", clipPath[0]);
      const cleanup = () => {
        isTransitioningRef.current = false;
        delete root.dataset.magicuiThemeVt;
        root.style.removeProperty("--magicui-theme-toggle-vt-duration");
        root.style.removeProperty("--magicui-theme-vt-clip-from");
      };

      isTransitioningRef.current = true;
      const transition = document.startViewTransition(() => {
        flushSync(applyTheme);
      });
      if (typeof transition?.finished?.finally === "function") {
        transition.finished.finally(cleanup).catch(() => {});
      } else {
        cleanup();
      }

      const ready = transition?.ready;
      if (ready && typeof ready.then === "function") {
        ready
          .then(() => {
            document.documentElement.animate(
              {
                clipPath,
              },
              {
                duration,
                easing: shape === "star" ? "linear" : "ease-in-out",
                fill: "forwards",
                pseudoElement: "::view-transition-new(root)",
              }
            );
          })
          .catch(() => {});
      }
    }, [shape, fromCenter, duration, isDark, setTheme]);

    return (
      <button
        type="button"
        ref={buttonRef}
        aria-label="Toggle color theme"
        onClick={toggleTheme}
        className={cn(
          "relative inline-flex size-9 cursor-pointer items-center justify-center rounded-full border border-border bg-background/60 text-foreground transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/60",
          className
        )}
        {...props}
      >
        <Sun className="size-4 rotate-0 scale-100 transition-transform duration-300 dark:-rotate-90 dark:scale-0" />
        <Moon className="absolute size-4 rotate-90 scale-0 transition-transform duration-300 dark:rotate-0 dark:scale-100" />
        <span className="sr-only">Toggle theme</span>
      </button>
    );
  }
);

AnimatedThemeToggle.displayName = "AnimatedThemeToggle";
