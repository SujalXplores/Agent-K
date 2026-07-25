import { listInvestigations } from "@/lib/agentk";

/** Read-only proxy to GET /api/investigations, for the console's live panel. */
export async function GET(req: Request) {
  try {
    return Response.json({ investigations: await listInvestigations(req.signal) });
  } catch {
    // The console shows "waiting for Agent K" rather than breaking, so a
    // restarting app doesn't blank the page mid-demo.
    return Response.json({ investigations: null }, { status: 200 });
  }
}
