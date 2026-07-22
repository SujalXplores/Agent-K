"use client";

import { ArrowRight, Pause, Play } from "lucide-react";
import { useState } from "react";

import { investigationSequence } from "../../data/content";
import styles from "./InvestigationRibbon.module.css";

export function InvestigationRibbon() {
  const [paused, setPaused] = useState(false);
  const controlLabel = paused
    ? "Play investigation sequence"
    : "Pause investigation sequence";

  return (
    <div
      className={`${styles.ribbon} ${paused ? styles.paused : ""}`}
      role="group"
      aria-label="Agent K investigation sequence"
    >
      <div className={styles.ribbonTrack}>
        {[false, true].map((duplicate) => (
          <div
            className={styles.ribbonSequence}
            aria-hidden={duplicate || undefined}
            key={duplicate ? "duplicate" : "primary"}
          >
            {investigationSequence.map((item) => (
              <span key={item}>
                {item}
                <ArrowRight aria-hidden="true" />
              </span>
            ))}
          </div>
        ))}
      </div>
      <button
        className={styles.control}
        type="button"
        aria-label={controlLabel}
        aria-pressed={paused}
        title={controlLabel}
        onClick={() => setPaused((current) => !current)}
      >
        {paused ? <Play aria-hidden="true" fill="currentColor" /> : <Pause aria-hidden="true" />}
      </button>
    </div>
  );
}
