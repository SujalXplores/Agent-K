export type TechIcon =
  | "signoz"
  | "opentelemetry"
  | "fastapi"
  | "groq"
  | "postgresql"
  | "docker"
  | "python"
  | "mcp";

export interface TechItem {
  name: string;
  role: string;
  href: string;
  icon: TechIcon;
}

export const techStack: TechItem[] = [
  {
    name: "SigNoz",
    role: "Traces, metrics, logs, dashboards and alerts",
    href: "https://signoz.io",
    icon: "signoz",
  },
  {
    name: "OpenTelemetry",
    role: "Open standard that instruments every step",
    href: "https://opentelemetry.io",
    icon: "opentelemetry",
  },
  {
    name: "FastAPI",
    role: "The Python web app being watched",
    href: "https://fastapi.tiangolo.com",
    icon: "fastapi",
  },
  {
    name: "Groq",
    role: "Fast, free-tier language model inference",
    href: "https://groq.com",
    icon: "groq",
  },
  {
    name: "PostgreSQL + pgvector",
    role: "One store for support docs and their vectors",
    href: "https://github.com/pgvector/pgvector",
    icon: "postgresql",
  },
  {
    name: "Docker",
    role: "Runs every service the same way each time",
    href: "https://www.docker.com",
    icon: "docker",
  },
  {
    name: "Python",
    role: "The language behind the app and the agent",
    href: "https://www.python.org",
    icon: "python",
  },
  {
    name: "Model Context Protocol",
    role: "How the agent queries SigNoz for evidence",
    href: "https://modelcontextprotocol.io",
    icon: "mcp",
  },
];
