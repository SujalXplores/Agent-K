"use client";

import { RotateCcw } from "lucide-react";
import { useReducedMotion } from "motion/react";
import { useEffect, useRef } from "react";

import { INCIDENT_REPLAY_EVENT } from "../../data/events";

type ReplayJumpButtonProps = {
  className: string | undefined;
};

function waitForScrollEnd(signal: AbortSignal) {
  return new Promise<void>((resolve) => {
    const finish = () => {
      window.clearTimeout(timer);
      document.removeEventListener("scrollend", finish);
      resolve();
    };
    const timer = window.setTimeout(finish, 900);

    document.addEventListener("scrollend", finish, { once: true, signal });
    signal.addEventListener("abort", finish, { once: true });
  });
}

export function ReplayJumpButton({ className }: ReplayJumpButtonProps) {
  const reduceMotion = useReducedMotion();
  const pending = useRef<AbortController | null>(null);

  useEffect(() => () => pending.current?.abort(), []);

  async function handleReplay() {
    pending.current?.abort();
    const controller = new AbortController();
    const target = document.querySelector<HTMLElement>("#live-demo");
    pending.current = controller;

    if (target) {
      target.scrollIntoView({
        behavior: reduceMotion ? "auto" : "smooth",
        block: "center",
      });
      if (!reduceMotion) await waitForScrollEnd(controller.signal);
    }

    if (controller.signal.aborted) return;
    pending.current = null;
    window.dispatchEvent(new Event(INCIDENT_REPLAY_EVENT));
  }

  return (
    <button className={className} type="button" onClick={handleReplay}>
      Replay the evidence run
      <RotateCcw aria-hidden="true" />
    </button>
  );
}
