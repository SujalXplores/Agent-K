import type {
  ChatModelAdapter,
  ChatModelRunOptions,
  ChatModelRunResult,
} from "@assistant-ui/react";
import type { AskResponse } from "@/lib/rag";

/** Pull the plain text out of the newest user message in the thread. */
function latestUserText(messages: ChatModelRunOptions["messages"]): string {
  for (let i = messages.length - 1; i >= 0; i--) {
    const message = messages[i];
    if (message.role !== "user") continue;

    return message.content
      .filter((part): part is { type: "text"; text: string } => part.type === "text")
      .map((part) => part.text)
      .join("\n")
      .trim();
  }

  return "";
}

/**
 * Bridges assistant-ui to the monitored RAG service.
 *
 * Only the newest question is sent. POST /ask is a single-turn, stateless
 * contract — {question} in, {answer, sources} out — so there is no
 * conversation history to forward, and pretending otherwise by concatenating
 * turns would change the prompt the instrumented service actually builds and
 * make the demo's traces stop matching the recorded eval runs.
 */
export const ragAdapter: ChatModelAdapter = {
  async run({ messages, abortSignal }): Promise<ChatModelRunResult> {
    const question = latestUserText(messages);

    if (!question) {
      return { content: [{ type: "text", text: "Ask me anything about Flowdeck." }] };
    }

    const response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
      signal: abortSignal,
    });

    if (!response.ok) {
      const { error } = (await response.json().catch(() => ({}))) as {
        error?: string;
      };
      // Thrown, not returned as text: assistant-ui renders a thrown adapter
      // error through its own error surface, which keeps a service failure
      // visually distinct from the assistant answering badly. Under the seeded
      // db-pool-exhaustion scenario that distinction is the whole point.
      throw new Error(error ?? "Flowdeck Support is unavailable right now.");
    }

    const { answer, sources } = (await response.json()) as AskResponse;

    return {
      content: [
        { type: "text", text: answer },
        ...sources.map((source) => ({
          type: "source" as const,
          sourceType: "document" as const,
          id: source.doc_id,
          title: source.title,
          mediaType: "text/markdown",
        })),
      ],
    };
  },
};
