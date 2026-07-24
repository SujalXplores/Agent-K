"use client";

import { Accordion } from "@base-ui/react/accordion";
import { ChevronDown } from "lucide-react";

import { content } from "@/lib/config/content";

export function FaqAccordion() {
  return (
    <Accordion.Root
      multiple={false}
      className="mx-auto flex max-w-3xl flex-col gap-3"
    >
      {content.faq.items.map((item, index) => (
        <Accordion.Item
          key={item.question}
          value={index}
          className="overflow-hidden rounded-xl border border-border bg-card/40"
        >
          <Accordion.Header className="m-0">
            <Accordion.Trigger className="group flex w-full cursor-pointer items-center justify-between gap-4 px-5 py-4 text-left text-base font-medium transition-colors hover:bg-accent/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring/50">
              {item.question}
              <ChevronDown className="size-4 shrink-0 text-muted-foreground transition-transform duration-300 group-data-[panel-open]:rotate-180 motion-reduce:transition-none" />
            </Accordion.Trigger>
          </Accordion.Header>
          <Accordion.Panel
            keepMounted
            className="h-[var(--accordion-panel-height)] overflow-hidden transition-[height] duration-300 ease-out data-[ending-style]:h-0 data-[starting-style]:h-0 motion-reduce:transition-none"
          >
            <p className="px-5 pb-4 text-sm leading-relaxed text-muted-foreground">
              {item.answer}
            </p>
          </Accordion.Panel>
        </Accordion.Item>
      ))}
    </Accordion.Root>
  );
}
