import { readFlags } from "@/lib/rag";

/**
 * Read-only proxy to GET /admin/flags, so the demo can show which failure
 * scenario is live without exposing the RAG service to the browser.
 *
 * Read-only on purpose: this route cannot toggle a scenario. Flipping a flag
 * is the demo operator's action, taken deliberately against /admin/flags with
 * the admin token — not something a page visitor can trigger.
 */
export async function GET(req: Request) {
  try {
    const state = await readFlags(req.signal);
    return Response.json(state);
  } catch {
    // The status strip degrades to "unknown" rather than breaking the page —
    // the assistant itself is still usable if this poll fails.
    return Response.json({ flags: null }, { status: 200 });
  }
}
