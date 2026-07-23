# Agent K Cinematic Design Review

## Hackathon context

Agents of SigNoz is a WeMakeDevs × SigNoz hackathon running July 20–26, 2026. Agent K targets Track 01, AI & Agent Observability. The six published criteria are impact, creativity, technical excellence, depth of SigNoz use, UX, and presentation quality; the organizer’s mission is to make AI workflows fully debuggable through traces, metrics, logs, dashboards, alerts, and token cost ([hackathon brief](https://www.wemakedevs.org/hackathons/signoz)). The seven-day scope and current polished landing page make a contained cinematic layer higher leverage than a redesign.

The audience is on-call engineers, SRE/platform teams operating LLM/RAG systems, and judges assessing whether Agent K is understandable, credible, safe, and deeply tied to SigNoz. The competitive set is AI-SRE investigation software, not generic agent chat.

## Winning-pattern review

Past WeMakeDevs winners show that complete, inspectable workflows beat decorative concept pages. DealDesk-Tambo exposes contract risk, clause refinement, obligations, and definitions as domain-specific interfaces; Fireflow turns intent into editable workflow nodes; Brilliant turns calendar intent into working forms and actions ([Tambo winners](https://www.wemakedevs.org/hackathons/tambo/projects)). Manthan and GSoC/Open-Source Matchmaker similarly shipped code, live experiences, and demos rather than static pitches ([Coral winners](https://www.wemakedevs.org/hackathons/coral/projects)). The design implication is to keep Agent K’s incident console and evidence packet as the hero; 3D should clarify their workflow, never compete with them.

Three domain references reinforce that decision. Datadog Bits emphasizes autonomous telemetry investigation and audit-ready RCA ([Datadog Bits](https://www.datadoghq.com/blog/building-bits-ai-sre/)); PagerDuty exposes investigation progress in real time rather than hiding it until a report is ready ([PagerDuty SRE Agent](https://www.pagerduty.com/eng/inside-pagerdutys-sre-agent-how-we-built-deep-incident-investigation/)); Honeycomb Canvas presents investigation steps and query results as a verifiable interactive notebook ([Honeycomb Canvas](https://www.honeycomb.io/platform/canvas)). Expected patterns are explicit progression, evidence visibility, restrained operational color, and a clear terminal state.

Current Awwwards Three.js references highlight scroll interaction, R3F component work, cinematic sequences, and shader-driven UI theming ([Awwwards Three.js collection](https://www.awwwards.com/elements/threejs/)). We adopt the motion language—persistent world, depth continuity, elegant camera drift, and state morphing—without copying layouts or assets. Content was rephrased for compliance with licensing restrictions.

## Visual direction

| Decision   | Choice                                                                                                        | Rationale                                                          |
| ---------- | ------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| Mood       | Future observability control center                                                                           | Technical, calm, inspectable; never gamer-like                     |
| Color      | Preserve current Apple-neutral surfaces; use blue telemetry, violet reasoning, coral incident, green verified | Existing brand remains intact and each signal has semantic meaning |
| Typography | Preserve Inter + Sora                                                                                         | Already legible and distinctive; no layout shift or redesign       |
| Density    | Preserve current spacing and product cards                                                                    | Judges must still read the evidence story instantly                |
| Motion     | Cinematic but subordinate, scroll-scrubbed with inertial camera easing                                        | Premium continuity without blocking interaction                    |
| Surface    | One fixed transparent WebGL layer below DOM content                                                           | Maintains semantics, keyboard behavior, and existing CTA positions |

## Scroll film

1. **Hero / alert enters:** sparse telemetry strands orbit an evidence core; a coral anomaly pulse arrives while the camera performs a subtle dolly.
2. **Problem / ambiguity:** the core opens into a service constellation; latency/error ripples reveal that one symptom can cross traces, logs, and metrics.
3. **Three Laws / constraint:** three luminous rings assemble around the core—evidence, policy, telemetry—forming a mechanical trust boundary.
4. **Protocol / chain of custody:** five nodes become a directed route: signal → observe → reason → govern → verify. One packet travels the path as the camera tracks laterally.
5. **Proof / root cause:** evidence strands converge on one service, competing nodes dim, and the policy gate resolves into a verified green recovery wave.
6. **Self-telemetry / observer observed:** a second orbital trace wraps the investigator itself; query, cost, and loop pulses remain visibly bounded.
7. **Final CTA / sealed report:** the system compacts into a stable proof core with a quiet success halo—resolution, not spectacle.

## Readiness and guardrails

- Existing section order, copy, typography, spacing, cards, CTAs, and responsive behavior remain unchanged.
- Wow elements: persistent scene continuity, procedural telemetry particles, anomaly propagation, three-ring gate assembly, camera chapter transitions, recovery ripple, pointer-reactive depth, and theme-aware lighting.
- Dark mode uses the same semantic hues with deeper backgrounds and brighter emissive accents; light mode lowers opacity so text contrast remains dominant.
- Reduced motion receives no WebGL animation; low-capability/coarse-pointer devices use fewer particles and lower DPR; all meaning remains in semantic HTML.
- Performance budget: one canvas, no external models/textures, no shadows or postprocessing, ≤9 primary draw calls, adaptive DPR 0.75–1.5, instanced/point geometry, lazy client loading, and WebGL-context fallback.
- Target: 60 FPS desktop, LCP under 2.5 seconds, no canvas-caused CLS, no pointer interception, and no false claim that illustrative telemetry is live.
- Deployment remains the existing static-first Next.js App Router build on Vercel; the cinematic chunk is client-only and route-local.
