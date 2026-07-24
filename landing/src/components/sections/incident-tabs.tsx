"use client";

import { Tabs } from "@base-ui/react/tabs";

import { content } from "@/lib/config/content";
import { cn } from "@/lib/utils";
import { IncidentCard } from "@/components/sections/incidents/incident-card";

const items = content.incidents.items;

export function IncidentTabs() {
  return (
    <Tabs.Root defaultValue={items[0].id} className="flex flex-col gap-8">
      <Tabs.List className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {items.map((incident) => (
          <Tabs.Tab
            key={incident.id}
            value={incident.id}
            className="border-border bg-card/40 hover:border-primary/30 data-selected:border-primary/50 data-selected:bg-accent/50 flex cursor-pointer flex-col items-start gap-1.5 rounded-xl border p-3 text-left transition-colors"
          >
            <span className="flex items-center gap-1.5">
              <span
                className={cn(
                  "size-1.5 rounded-full",
                  incident.verdict === "allow" ? "bg-law-2" : "bg-destructive"
                )}
              />
              <span className="text-muted-foreground font-mono text-[11px]">
                {String(incident.index).padStart(2, "0")}
              </span>
            </span>
            <span className="text-sm font-medium">{incident.tag}</span>
          </Tabs.Tab>
        ))}
      </Tabs.List>

      {items.map((incident) => (
        <Tabs.Panel
          key={incident.id}
          value={incident.id}
          keepMounted
          className="outline-none"
        >
          <IncidentCard incident={incident} />
        </Tabs.Panel>
      ))}
    </Tabs.Root>
  );
}
