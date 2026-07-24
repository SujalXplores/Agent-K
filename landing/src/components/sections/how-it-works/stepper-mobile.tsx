"use client";

import { Tabs } from "@base-ui/react/tabs";

import { pad, steps } from "@/components/sections/how-it-works/constants";

export function StepperMobile() {
  return (
    <Tabs.Root defaultValue="1" className="flex flex-col gap-5">
      <Tabs.List className="no-scrollbar flex gap-2 overflow-x-auto pb-1">
        {steps.map((step) => (
          <Tabs.Tab
            key={step.index}
            value={String(step.index)}
            className="border-border text-muted-foreground data-selected:bg-primary data-selected:text-primary-foreground flex size-9 shrink-0 cursor-pointer items-center justify-center rounded-full border font-mono text-sm transition-colors data-selected:border-transparent"
          >
            {step.index}
          </Tabs.Tab>
        ))}
      </Tabs.List>

      {steps.map((step) => (
        <Tabs.Panel
          key={step.index}
          value={String(step.index)}
          className="border-border bg-card/40 min-h-28 rounded-2xl border p-5 outline-none"
        >
          <span className="text-primary font-mono text-xs">
            {pad(step.index)}
          </span>
          <h3 className="mt-1 text-lg font-semibold tracking-tight">
            {step.title}
          </h3>
          <p className="text-muted-foreground mt-1.5 text-sm leading-relaxed">
            {step.description}
          </p>
        </Tabs.Panel>
      ))}
    </Tabs.Root>
  );
}
