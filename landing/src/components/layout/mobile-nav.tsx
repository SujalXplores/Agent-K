"use client";

import { useState } from "react";
import { Dialog } from "@base-ui/react/dialog";
import { Menu, X } from "lucide-react";

import { GitHubIcon } from "@/components/icons/github";
import { Logo } from "@/components/layout/logo";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { buttonVariants } from "@/components/ui/button";
import { content } from "@/lib/config/content";
import { siteConfig } from "@/lib/config/site";
import { cn } from "@/lib/utils";

export function MobileNav() {
  const [open, setOpen] = useState(false);

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger
        aria-label="Open menu"
        className={cn(
          buttonVariants({ variant: "outline", size: "icon" }),
          "rounded-full md:hidden"
        )}
      >
        <Menu className="size-4" />
      </Dialog.Trigger>

      <Dialog.Portal>
        <Dialog.Backdrop className="fixed inset-0 z-[70] bg-black/50 backdrop-blur-sm transition-opacity duration-300 data-[ending-style]:opacity-0 data-[starting-style]:opacity-0" />
        <Dialog.Popup
          className={cn(
            "fixed inset-y-0 right-0 z-[80] flex w-[min(20rem,90vw)] flex-col gap-8 border-l border-border bg-background p-6 shadow-2xl outline-none",
            "transition-all duration-300 ease-out",
            "data-[starting-style]:translate-x-full data-[starting-style]:opacity-0",
            "data-[ending-style]:translate-x-full data-[ending-style]:opacity-0"
          )}
        >
          <div className="flex items-center justify-between">
            <Logo />
            <Dialog.Title className="sr-only">Site navigation</Dialog.Title>
            <Dialog.Close
              aria-label="Close menu"
              className={cn(
                buttonVariants({ variant: "ghost", size: "icon" }),
                "rounded-full"
              )}
            >
              <X className="size-4" />
            </Dialog.Close>
          </div>

          <nav aria-label="Mobile">
            <ul className="flex flex-col gap-1">
              {siteConfig.nav.map((item) => (
                <li key={item.href}>
                  <a
                    href={item.href}
                    onClick={() => setOpen(false)}
                    className="flex items-center rounded-lg px-3 py-2.5 text-base font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                  >
                    {item.label}
                  </a>
                </li>
              ))}
            </ul>
          </nav>

          <div className="mt-auto flex flex-col gap-4">
            <a
              href={siteConfig.links.github}
              target="_blank"
              rel="noopener noreferrer"
              onClick={() => setOpen(false)}
              className={cn(
                buttonVariants({ variant: "default" }),
                "h-10 w-full gap-2 rounded-full"
              )}
            >
              <GitHubIcon className="size-4" />
              {content.hero.primaryCta.label}
            </a>
            <div className="flex items-center justify-between rounded-lg border border-border px-3 py-2">
              <span className="text-sm text-muted-foreground">Theme</span>
              <ThemeToggle />
            </div>
          </div>
        </Dialog.Popup>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
