"use client";

import { useEffect, useState } from "react";

import { Logo } from "@/components/layout/logo";
import { MobileNav } from "@/components/layout/mobile-nav";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { useActiveSection } from "@/hooks/use-active-section";
import { siteConfig } from "@/lib/config/site";
import { cn } from "@/lib/utils";

const SECTION_IDS = siteConfig.nav.map((item) => item.href.replace("#", ""));

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const activeId = useActiveSection(SECTION_IDS);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={cn(
        "sticky top-0 z-50 transition-all duration-300",
        scrolled ? "px-3 pt-3 sm:px-4" : "px-0 pt-0"
      )}
    >
      <div
        className={cn(
          "mx-auto flex items-center justify-between gap-4 transition-all duration-300",
          scrolled
            ? "border-border/70 bg-background/70 h-14 max-w-4xl rounded-full border px-4 shadow-lg shadow-black/6 backdrop-blur-md sm:px-5"
            : "h-16 max-w-(--container-max) rounded-none border border-transparent px-6"
        )}
      >
        <a
          href="#hero"
          aria-label="Agent K, back to top"
          className="focus-visible:ring-ring/60 rounded-md focus-visible:ring-2 focus-visible:outline-none"
        >
          <Logo />
        </a>

        <nav aria-label="Primary" className="hidden md:block">
          <ul className="flex items-center gap-1">
            {siteConfig.nav.map((item) => {
              const id = item.href.replace("#", "");
              const isActive = activeId === id;
              return (
                <li key={item.href}>
                  <a
                    href={item.href}
                    aria-current={isActive ? "true" : undefined}
                    className={cn(
                      "inline-flex rounded-full px-3.5 py-2 text-sm font-medium transition-colors",
                      isActive
                        ? "bg-accent text-foreground"
                        : "text-muted-foreground hover:text-foreground"
                    )}
                  >
                    {item.label}
                  </a>
                </li>
              );
            })}
          </ul>
        </nav>

        <div className="flex items-center gap-2">
          <ThemeToggle />
          <MobileNav />
        </div>
      </div>
    </header>
  );
}
