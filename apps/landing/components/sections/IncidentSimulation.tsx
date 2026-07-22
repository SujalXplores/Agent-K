"use client";

import {
  Activity,
  Check,
  CircleCheck,
  FileText,
  GitBranch,
  GitCommitHorizontal,
  Play,
  RotateCcw,
  Search,
  ShieldCheck,
  TriangleAlert,
} from "lucide-react";
import { AnimatePresence, m, useInView, useReducedMotion } from "motion/react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { incidentEvidence, incidentStages } from "../../data/content";
import { INCIDENT_REPLAY_EVENT } from "../../data/events";
import { MOTION_TRANSITION } from "../motion/constants";
import styles from "./IncidentSimulation.module.css";

const chartValues = [14, 12, 15, 13, 17, 15, 19, 18, 24, 22, 30, 44, 69, 81, 76, 88, 84, 93] as const;
const stageIcons = [TriangleAlert, Search, GitBranch, ShieldCheck, CircleCheck] as const;
const evidenceIcons = {
  trace: Activity,
  log: FileText,
  deploy: GitCommitHorizontal,
} as const;
const START_DELAY = 160;
const STAGE_INTERVAL = 560;
const AUTOPLAY_DELAY = 420;

export function IncidentSimulation() {
  const cardRef = useRef<HTMLElement | null>(null);
  const timers = useRef<Array<ReturnType<typeof setTimeout>>>([]);
  const hasAutoplayed = useRef(false);
  const [activeStage, setActiveStage] = useState(-1);
  const [running, setRunning] = useState(false);
  const reduceMotion = useReducedMotion();
  const inView = useInView(cardRef, { once: true, amount: 0.42 });

  const clearTimers = useCallback(() => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
  }, []);

  const runSimulation = useCallback(() => {
    clearTimers();
    setActiveStage(-1);

    if (reduceMotion) {
      setActiveStage(incidentStages.length - 1);
      setRunning(false);
      return;
    }

    setRunning(true);
    incidentStages.forEach((_, index) => {
      const timer = setTimeout(() => {
        setActiveStage(index);
        if (index === incidentStages.length - 1) setRunning(false);
      }, START_DELAY + index * STAGE_INTERVAL);
      timers.current.push(timer);
    });
  }, [clearTimers, reduceMotion]);

  useEffect(() => clearTimers, [clearTimers]);

  useEffect(() => {
    function handleReplay() {
      runSimulation();
    }

    window.addEventListener(INCIDENT_REPLAY_EVENT, handleReplay);
    return () => window.removeEventListener(INCIDENT_REPLAY_EVENT, handleReplay);
  }, [runSimulation]);

  useEffect(() => {
    if (!inView || hasAutoplayed.current) return;
    hasAutoplayed.current = true;

    const timer = setTimeout(runSimulation, reduceMotion ? 0 : AUTOPLAY_DELAY);
    timers.current.push(timer);
  }, [inView, reduceMotion, runSimulation]);

  const evidenceCount = activeStage >= 2 ? 3 : activeStage >= 1 ? 1 : 0;
  const status = activeStage >= 0
    ? incidentStages[activeStage]?.status ?? "Standing by for evidence"
    : "Standing by for evidence";
  const gateState = activeStage >= 4 ? "verified" : activeStage >= 3 ? "allowed" : "idle";
  const gateChecks = activeStage >= 3 ? 6 : activeStage >= 2 ? 3 : activeStage >= 1 ? 1 : 0;
  const buttonLabel = running ? "Restart" : activeStage >= 4 ? "Replay" : "Run";
  const stageProgress = activeStage < 0 ? 0 : (activeStage + 1) / incidentStages.length;
  const chartBars = useMemo(
    () =>
      chartValues.map((height, index) => ({
        height,
        delay: Math.min(index * 0.022, 0.28),
      })),
    [],
  );

  return (
    <article
      className={styles.console}
      id="live-demo"
      ref={cardRef}
      aria-busy={running}
      aria-label="Controlled incident investigation simulation"
    >
      <header className={styles.consoleHeader}>
        <div>
          <span className={styles.consoleK} aria-hidden="true">K</span>
          <span>
            <small>Black box / K-01</small>
            <strong>INC-042 · support-api</strong>
          </span>
        </div>
        <span className={`${styles.recording} ${running ? styles.recordingActive : ""}`}>
          <i aria-hidden="true" />
          Controlled trace
        </span>
      </header>

      <div className={styles.incidentHead}>
        <div>
          <span>Signal</span>
          <strong>Failed answers after v2 deploy</strong>
        </div>
        <span className={styles.severity}>P1</span>
      </div>

      <div
        className={styles.chart}
        role="img"
        aria-label="Illustrative error rate rising from 1.1 percent to 8.4 percent after deployment v2"
      >
        <div className={styles.chartMeta}>
          <span>Error rate / illustrative</span>
          <strong>8.4%</strong>
        </div>
        <div className={styles.chartField} aria-hidden="true">
          <span className={styles.axisTop}>8.4</span>
          <span className={styles.axisBottom}>1.1</span>
          <div className={styles.deployMarker}><span>deploy v2</span></div>
          <div className={styles.policyMarker}>Policy / allow</div>
          <div className={styles.bars}>
            {chartBars.map((bar, index) => (
              <m.i
                key={`${bar.height}-${index}`}
                style={{ height: `${bar.height}%` }}
                initial={false}
                animate={{ scaleY: activeStage >= 0 ? 1 : 0.18, opacity: activeStage >= 0 ? 1 : 0.4 }}
                transition={
                  reduceMotion
                    ? MOTION_TRANSITION.instant
                    : { ...MOTION_TRANSITION.chart, delay: bar.delay }
                }
              />
            ))}
          </div>
        </div>
      </div>

      <div className={styles.consoleBody}>
        <div className={styles.stageColumn}>
          <span className={styles.stageRail} aria-hidden="true">
            <m.i
              initial={false}
              animate={{ scaleY: stageProgress }}
              transition={reduceMotion ? MOTION_TRANSITION.instant : MOTION_TRANSITION.movement}
            />
          </span>
          <ol className={styles.stages} aria-label="Investigation stages">
            {incidentStages.map((stage, index) => {
              const StageIcon = stageIcons[index] ?? Search;
              const isCurrent = activeStage === index && index !== incidentStages.length - 1;
              const isComplete = activeStage > index || (activeStage === 4 && index === 4);
              return (
                <m.li
                  className={`${isCurrent ? styles.current : ""} ${isComplete ? styles.complete : ""}`}
                  key={stage.title}
                  initial={false}
                  animate={{ opacity: isCurrent || isComplete ? 1 : 0.38, x: isCurrent ? 6 : 0 }}
                  transition={reduceMotion ? MOTION_TRANSITION.instant : MOTION_TRANSITION.movement}
                  aria-current={isCurrent ? "step" : undefined}
                >
                  <m.span
                    className={styles.stageIcon}
                    animate={{ scale: isCurrent ? 1.08 : 1 }}
                    transition={reduceMotion ? MOTION_TRANSITION.instant : MOTION_TRANSITION.movement}
                  >
                    <StageIcon aria-hidden="true" />
                  </m.span>
                  <span>
                    <strong>{stage.title}</strong>
                    <small>{stage.detail}</small>
                  </span>
                </m.li>
              );
            })}
          </ol>
        </div>

        <div className={styles.packet}>
          <div className={styles.packetHead}>
            <span>Evidence packet</span>
            <strong>{evidenceCount} / 3</strong>
          </div>
          <ul>
            {incidentEvidence.map((item, index) => {
              const EvidenceIcon = evidenceIcons[item.kind];
              const found = index < evidenceCount;
              return (
                <m.li
                  key={item.title}
                  initial={false}
                  animate={{ opacity: found ? 1 : 0.3, x: found ? 0 : 8, scale: found ? 1 : 0.985 }}
                  transition={reduceMotion ? MOTION_TRANSITION.instant : MOTION_TRANSITION.entrance}
                >
                  <span className={`${styles.evidenceIcon} ${styles[item.kind]}`}>
                    <EvidenceIcon aria-hidden="true" />
                  </span>
                  <span>
                    <strong>{item.title}</strong>
                    <small>{item.detail}</small>
                  </span>
                  <Check className={styles.evidenceCheck} aria-hidden="true" />
                </m.li>
              );
            })}
          </ul>
        </div>
      </div>

      <footer className={`${styles.gate} ${styles[gateState]}`}>
        <span className={styles.gateIcon}>
          <ShieldCheck aria-hidden="true" />
        </span>
        <span className={styles.gateCopy}>
          <small>Deterministic policy gate</small>
          <span className={styles.statusViewport} role="status" aria-live="polite" aria-atomic="true">
            <AnimatePresence initial={false} mode="wait">
              <m.strong
                key={status}
                initial={reduceMotion ? false : { opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={reduceMotion ? { opacity: 1 } : { opacity: 0, y: -5 }}
                transition={reduceMotion ? MOTION_TRANSITION.instant : MOTION_TRANSITION.status}
              >
                {status}
              </m.strong>
            </AnimatePresence>
          </span>
          <span className={styles.gateChecks} aria-hidden="true">
            {Array.from({ length: 6 }).map((_, i) => (
              <m.i
                key={i}
                animate={{
                  backgroundColor: i < gateChecks ? 'var(--acid)' : 'rgba(255,255,255,0.08)',
                  scaleX: i < gateChecks ? 1 : 0.4,
                }}
                transition={reduceMotion ? MOTION_TRANSITION.instant : { ...MOTION_TRANSITION.fast, delay: i * 0.04 }}
              />
            ))}
            <small>{gateChecks} / 6 rules</small>
          </span>
        </span>
        <button type="button" onClick={runSimulation}>
          {running ? <RotateCcw aria-hidden="true" /> : <Play aria-hidden="true" fill="currentColor" />}
          {buttonLabel}
        </button>
      </footer>

      <p className={styles.disclaimer}>Controlled scenario · no production action</p>
    </article>
  );
}
