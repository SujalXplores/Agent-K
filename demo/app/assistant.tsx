"use client";

import { AssistantRuntimeProvider, useLocalRuntime } from "@assistant-ui/react";
import { Thread } from "@/components/assistant-ui/thread";
import { AppHeader } from "@/components/flowdeck/app-header";
import { IncidentStrip } from "@/components/flowdeck/incident-strip";
import { ragAdapter } from "@/lib/rag-adapter";

export const Assistant = () => {
  const runtime = useLocalRuntime(ragAdapter);

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <div className="flex h-dvh flex-col">
        <AppHeader />
        <IncidentStrip />
        <div className="min-h-0 flex-1">
          <Thread />
        </div>
      </div>
    </AssistantRuntimeProvider>
  );
};
