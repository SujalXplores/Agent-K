export const cssVar = {
  primary: "var(--primary)",
  foreground: "var(--foreground)",
  background: "var(--background)",
  border: "var(--border)",
  muted: "var(--muted)",
  law1: "var(--law-1)",
  law2: "var(--law-2)",
  law3: "var(--law-3)",
  success: "var(--success)",
  destructive: "var(--destructive)",
} as const;

export const brandColor = {
  primary: "#2563eb",
  law1: "#2563eb",
  law2: "#10b981",
  law3: "#8b5cf6",
  success: "#10b981",
  destructive: "#ef4444",
  cyan: "#22b8cf",
  amber: "#f59e0b",
} as const;

export const motion = {
  duration: {
    fast: 0.15,
    base: 0.3,
    slow: 0.6,
  },
  ease: {
    outExpo: [0.16, 1, 0.3, 1] as const,
    inOutSmooth: [0.65, 0, 0.35, 1] as const,
    spring: [0.34, 1.56, 0.64, 1] as const,
  },
  stagger: 0.08,
} as const;

export type LawKey = "law-1" | "law-2" | "law-3";

export const lawTokens: Record<
  LawKey,
  { color: string; foreground: string; muted: string; brand: string }
> = {
  "law-1": {
    color: "var(--law-1)",
    foreground: "var(--law-1-foreground)",
    muted: "var(--law-1-muted)",
    brand: brandColor.law1,
  },
  "law-2": {
    color: "var(--law-2)",
    foreground: "var(--law-2-foreground)",
    muted: "var(--law-2-muted)",
    brand: brandColor.law2,
  },
  "law-3": {
    color: "var(--law-3)",
    foreground: "var(--law-3-foreground)",
    muted: "var(--law-3-muted)",
    brand: brandColor.law3,
  },
};
