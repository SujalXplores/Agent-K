"use client";

import { m, useReducedMotion, useScroll, useSpring } from "motion/react";

import styles from "./ScrollProgress.module.css";

export function ScrollProgress() {
  const reduceMotion = useReducedMotion();
  const { scrollYProgress } = useScroll();
  const smoothProgress = useSpring(scrollYProgress, {
    stiffness: 180,
    damping: 32,
    restDelta: 0.001,
  });

  return (
    <div className={styles.track} aria-hidden="true">
      <m.div
        className={styles.bar}
        style={{ scaleX: reduceMotion ? scrollYProgress : smoothProgress }}
      />
    </div>
  );
}
