import { ExternalLinkIcon } from "lucide-react";
import type { FC } from "react";
import { FlowdeckLogo } from "@/components/flowdeck/logo";
import { BRAND } from "@/lib/flowdeck";

/**
 * One external link out of the demo. Rendered only when the corresponding env
 * var is set, so a bare `npm run dev` doesn't show dead links.
 */
const HeaderLink: FC<{ href?: string; label: string }> = ({ href, label }) => {
  if (!href) return null;

  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="text-muted-foreground hover:text-foreground inline-flex items-center gap-1 text-sm transition-colors"
    >
      {label}
      <ExternalLinkIcon className="size-3" aria-hidden />
    </a>
  );
};

export const AppHeader: FC = () => {
  return (
    <header className="border-border/60 flex shrink-0 items-center justify-between gap-4 border-b px-4 py-3">
      <div className="flex items-center gap-2.5">
        <FlowdeckLogo className="text-foreground size-5" />
        <div className="flex flex-col leading-none">
          <span className="text-sm font-semibold">{BRAND.name}</span>
          <span className="text-muted-foreground text-xs">Help centre</span>
        </div>
      </div>

      <nav className="flex items-center gap-4">
        <HeaderLink href={process.env.NEXT_PUBLIC_REPORTS_URL} label="Incident reports" />
        <HeaderLink href={process.env.NEXT_PUBLIC_SIGNOZ_DASHBOARD_URL} label="Live telemetry" />
      </nav>
    </header>
  );
};
