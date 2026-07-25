import { RagServiceError, ask } from "@/lib/rag";

/**
 * Server-side proxy to the monitored RAG service's POST /ask.
 *
 * The browser only ever talks to this route; this route is the only thing that
 * talks to FastAPI. See lib/rag.ts for why the boundary sits here.
 */
export async function POST(req: Request) {
  let question: unknown;

  try {
    ({ question } = (await req.json()) as { question?: unknown });
  } catch {
    return Response.json({ error: "Malformed request body." }, { status: 400 });
  }

  if (typeof question !== "string" || question.trim().length === 0) {
    return Response.json({ error: "A non-empty question is required." }, { status: 400 });
  }

  // Mirrors AskRequest's max_length=2000 so an over-long question fails here
  // rather than as an opaque 422 from FastAPI's validator.
  if (question.length > 2000) {
    return Response.json({ error: "Question exceeds the 2000 character limit." }, { status: 400 });
  }

  try {
    const result = await ask(question, req.signal);
    return Response.json(result);
  } catch (error) {
    if (error instanceof RagServiceError) {
      // 502, not the upstream status: the failure is this app's inability to
      // get an answer out of its dependency, and collapsing it to the upstream
      // code would misreport a 500 in the RAG service as a 500 in the UI.
      return Response.json({ error: error.message }, { status: 502 });
    }

    if (error instanceof Error && error.name === "AbortError") {
      return Response.json({ error: "Request cancelled." }, { status: 499 });
    }

    return Response.json(
      {
        error:
          "Could not reach Flowdeck Support. Check that the RAG service is running and RAG_API_URL is correct.",
      },
      { status: 502 },
    );
  }
}
