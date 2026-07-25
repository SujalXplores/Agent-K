"use client";

import { FileTextIcon } from "lucide-react";
import type { FC } from "react";

/**
 * Renders one retrieved corpus document as a citation chip.
 *
 * These are the `sources` POST /ask returns — the docs the pgvector similarity
 * search actually retrieved for this answer. They are the customer-visible face
 * of grounding: when the prompt-regression scenario is live and answers stop
 * being grounded, the absence of sensible citations here is what a user notices
 * before anyone reads a trace.
 */
export const SourceCitation: FC<{ title: string; docId: string }> = ({ title, docId }) => {
  return (
    <span
      data-slot="flowdeck_source-citation"
      title={docId}
      className="border-border/60 bg-muted/40 text-muted-foreground inline-flex max-w-full items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs"
    >
      <FileTextIcon className="size-3 shrink-0" aria-hidden />
      <span className="truncate">{title}</span>
    </span>
  );
};

/** Wrapper that labels the citation row beneath an answer. */
export const SourceCitationList: FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div
      data-slot="flowdeck_source-citations"
      className="mt-3 flex flex-wrap items-center gap-1.5 empty:hidden"
    >
      <span className="text-muted-foreground/70 mr-0.5 text-xs font-medium">Sources</span>
      {children}
    </div>
  );
};
