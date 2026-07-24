"use client";

import { useTheme } from "next-themes";

import { FlickeringGrid } from "@/components/ui/flickering-grid";
import { siteConfig } from "@/lib/config/site";

const wordmarkSvg = `<svg xmlns='http://www.w3.org/2000/svg' width='1200' height='260'><text x='50%' y='55%' dominant-baseline='middle' text-anchor='middle' font-family='ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif' font-size='240' font-weight='800' letter-spacing='-12'>${siteConfig.name}</text></svg>`;
const wordmarkMask = `url("data:image/svg+xml,${encodeURIComponent(wordmarkSvg)}")`;

export function FooterFlicker() {
  const { resolvedTheme } = useTheme();
  const color = resolvedTheme === "light" ? "#334155" : "#e2e8f0";

  return (
    <div
      aria-hidden="true"
      className="relative mt-14 h-40 w-full overflow-hidden select-none sm:h-48 md:h-60"
    >
      <FlickeringGrid
        className="absolute inset-0 mask-[linear-gradient(to_top,black,transparent_88%)]"
        color={color}
        squareSize={3}
        gridGap={7}
        maxOpacity={0.1}
        flickerChance={0.07}
      />
      <div
        className="absolute inset-0"
        style={{
          maskImage: wordmarkMask,
          WebkitMaskImage: wordmarkMask,
          maskRepeat: "no-repeat",
          WebkitMaskRepeat: "no-repeat",
          maskPosition: "center 62%",
          WebkitMaskPosition: "center 62%",
          maskSize: "contain",
          WebkitMaskSize: "contain",
        }}
      >
        <FlickeringGrid
          className="size-full"
          color={color}
          squareSize={3}
          gridGap={5}
          maxOpacity={0.55}
          flickerChance={0.16}
        />
      </div>
      <div className="to-background pointer-events-none absolute inset-0 bg-linear-to-t from-transparent from-30%" />
    </div>
  );
}
