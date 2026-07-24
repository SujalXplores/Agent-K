"use client";

import { Dialog } from "@base-ui/react/dialog";
import { Play, X } from "lucide-react";

import { buttonVariants } from "@/components/ui/button";
import { content } from "@/lib/config/content";
import { cn } from "@/lib/utils";

interface DemoDialogProps {
  label?: string;
  triggerVariant?: "default" | "outline" | "secondary" | "ghost";
  triggerClassName?: string;
}

export function DemoDialog({
  label = content.hero.secondaryCta.label,
  triggerVariant = "outline",
  triggerClassName,
}: DemoDialogProps) {
  return (
    <Dialog.Root>
      <Dialog.Trigger
        className={cn(
          buttonVariants({ variant: triggerVariant }),
          "text-foreground h-11 gap-2 rounded-full px-5 text-sm",
          triggerClassName
        )}
      >
        <Play className="size-4" />
        {label}
      </Dialog.Trigger>

      <Dialog.Portal>
        <Dialog.Backdrop className="fixed inset-0 z-70 bg-black/60 backdrop-blur-sm transition-opacity duration-300 data-ending-style:opacity-0 data-starting-style:opacity-0" />
        <Dialog.Popup
          className={cn(
            "border-border bg-card fixed top-1/2 left-1/2 z-80 w-[min(56rem,92vw)] -translate-x-1/2 -translate-y-1/2 rounded-2xl border p-2 shadow-2xl outline-none",
            "transition-all duration-300 ease-out",
            "data-starting-style:scale-95 data-starting-style:opacity-0",
            "data-ending-style:scale-95 data-ending-style:opacity-0"
          )}
        >
          <div className="flex items-center justify-between px-3 py-2">
            <Dialog.Title className="text-sm font-medium">
              {content.hero.demo.title}
            </Dialog.Title>
            <Dialog.Close
              aria-label="Close demo"
              className={cn(
                buttonVariants({ variant: "ghost", size: "icon" }),
                "rounded-full"
              )}
            >
              <X className="size-4" />
            </Dialog.Close>
          </div>
          <div className="bg-radial-primary border-border relative flex aspect-video w-full flex-col items-center justify-center gap-4 overflow-hidden rounded-xl border text-center">
            <div className="border-primary/40 bg-primary/10 flex size-16 items-center justify-center rounded-full border">
              <Play className="text-primary size-6" />
            </div>
            <p className="text-base font-medium">{content.hero.demo.poster}</p>
            <p className="text-muted-foreground max-w-sm px-6 text-sm">
              {content.hero.demo.note}
            </p>
          </div>
        </Dialog.Popup>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
