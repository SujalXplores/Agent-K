import { ImageResponse } from "next/og";

import { siteConfig } from "@/lib/config/site";
import { OG_CONTENT_TYPE, OG_SIZE } from "@/lib/seo/og";

export const alt = siteConfig.ogImageAlt;
export const size = OG_SIZE;
export const contentType = OG_CONTENT_TYPE;

const laws = [
  { n: "1", label: "Evidence", color: "#3b82f6" },
  { n: "2", label: "Action", color: "#10b981" },
  { n: "3", label: "Telemetry", color: "#a78bfa" },
];

export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          height: "100%",
          width: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "72px",
          backgroundColor: "#0b1020",
          backgroundImage:
            "radial-gradient(1000px 500px at 80% -10%, rgba(37,99,235,0.35), transparent), radial-gradient(800px 500px at 0% 120%, rgba(139,92,246,0.22), transparent)",
          color: "#f4f6fb",
          fontFamily: "sans-serif",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "18px" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                width: "56px",
                height: "56px",
                borderRadius: "16px",
                backgroundColor: "#2563eb",
                fontSize: "34px",
                fontWeight: 800,
                color: "#ffffff",
              }}
            >
              K
            </div>
            <div
              style={{
                fontSize: "34px",
                fontWeight: 700,
                letterSpacing: "-0.02em",
              }}
            >
              Agent K
            </div>
          </div>
          <div
            style={{
              display: "flex",
              fontSize: "22px",
              color: "#9fb0d0",
              border: "1px solid rgba(159,176,208,0.3)",
              borderRadius: "999px",
              padding: "10px 22px",
            }}
          >
            Agents of SigNoz
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          <div
            style={{
              display: "flex",
              fontSize: "68px",
              fontWeight: 800,
              lineHeight: 1.05,
              letterSpacing: "-0.03em",
              maxWidth: "980px",
            }}
          >
            Don&apos;t just trust an AI agent. Make it prove every step.
          </div>
          <div
            style={{
              display: "flex",
              fontSize: "28px",
              color: "#aebbd6",
              maxWidth: "900px",
            }}
          >
            Evidence-backed findings. One safe action. Every decision on the
            record.
          </div>
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", gap: "16px" }}>
            {laws.map((law) => (
              <div
                key={law.n}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "12px",
                  padding: "12px 20px",
                  borderRadius: "14px",
                  backgroundColor: "rgba(255,255,255,0.05)",
                  border: "1px solid rgba(255,255,255,0.08)",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    width: "14px",
                    height: "14px",
                    borderRadius: "999px",
                    backgroundColor: law.color,
                  }}
                />
                <div style={{ display: "flex", fontSize: "24px", color: "#dbe3f4" }}>
                  Law {law.n} · {law.label}
                </div>
              </div>
            ))}
          </div>
          <div
            style={{ display: "flex", fontSize: "24px", color: "#7c8bb0" }}
          >
            agent-k
          </div>
        </div>
      </div>
    ),
    { ...size }
  );
}
