import { fireAlert, generateTraffic, listInvestigations, setOnlyScenario } from "@/lib/agentk";
import { FLAG_NAMES } from "@/lib/flowdeck";

/**
 * Run one demo scenario end to end, the way the eval harness does
 * (scripts/run_eval.py): set the flag, put real traffic through /ask, fire the
 * alert webhook, then report which investigation ids existed beforehand so the
 * client can identify the new one.
 *
 * Deliberately does NOT wait for the investigation to finish. Agent K runs it as
 * a background task; blocking here would tie the demo's responsiveness to LLM
 * latency and hide the state machine actually progressing — which is the part
 * worth watching.
 */
export async function POST(req: Request) {
  let body: { scenario?: unknown; traffic?: unknown };
  try {
    body = (await req.json()) as typeof body;
  } catch {
    return Response.json({ error: "Malformed request body." }, { status: 400 });
  }

  const { scenario } = body;
  if (typeof scenario !== "string" || !FLAG_NAMES.includes(scenario)) {
    return Response.json(
      { error: `scenario must be one of ${FLAG_NAMES.join(", ")}` },
      { status: 400 },
    );
  }

  const traffic = typeof body.traffic === "number" ? Math.min(10, Math.max(1, body.traffic)) : 3;

  try {
    const before = (await listInvestigations()).map((i) => i.id);

    await setOnlyScenario(scenario);
    const served = await generateTraffic(traffic);
    await fireAlert(scenario);

    return Response.json({ scenario, served, requested: traffic, knownIds: before });
  } catch (error) {
    return Response.json(
      { error: error instanceof Error ? error.message : "scenario run failed" },
      { status: 502 },
    );
  }
}

/** Clear every scenario — the "return to healthy" control. */
export async function DELETE() {
  try {
    await setOnlyScenario(null);
    return Response.json({ scenario: null });
  } catch (error) {
    return Response.json(
      { error: error instanceof Error ? error.message : "could not clear scenarios" },
      { status: 502 },
    );
  }
}
