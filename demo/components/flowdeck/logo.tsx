import type { FC } from "react";

/** Flowdeck mark — three stacked lanes, a nod to the board/deck metaphor. */
export const FlowdeckLogo: FC<{ className?: string }> = ({ className }) => {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden
    >
      <rect x="3" y="4" width="18" height="4.5" rx="1.5" fill="currentColor" />
      <rect x="3" y="10.5" width="12" height="4.5" rx="1.5" fill="currentColor" opacity="0.65" />
      <rect x="3" y="17" width="7" height="4.5" rx="1.5" fill="currentColor" opacity="0.35" />
    </svg>
  );
};
