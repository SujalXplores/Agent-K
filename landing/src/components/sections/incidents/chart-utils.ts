import type { Incident } from "@/lib/config/content";

export function buildChartPaths(incident: Incident) {
  const { series, threshold } = incident;
  const values = threshold != null ? [...series, threshold] : series;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const W = 100;
  const H = 44;
  const top = 5;
  const plot = 34;
  const xFor = (i: number) => (i / (series.length - 1)) * W;
  const yFor = (v: number) => top + (1 - (v - min) / range) * plot;

  const line = series
    .map(
      (v, i) => `${i === 0 ? "M" : "L"}${xFor(i).toFixed(1)},${yFor(v).toFixed(1)}`
    )
    .join(" ");
  const area = `${line} L${W},${H} L0,${H} Z`;

  return { W, H, top, plot, xFor, yFor, line, area };
}
