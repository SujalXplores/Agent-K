import { ArrowDown, Play } from 'lucide-react';

import { trustItems } from '../../data/content';
import { Reveal } from '../motion/Reveal';
import { IncidentSimulation } from './IncidentSimulation';
import { InvestigationRibbon } from './InvestigationRibbon';
import styles from './Hero.module.css';

export function Hero() {
  return (
    <>
      <section className={styles.hero} id="top" aria-labelledby="hero-title">
        <Reveal
          ariaHidden
          className={styles.caseLine}
          delay={0.02}
          variant="fade"
        >
          <span>Case file / K-2026</span>
          <span>Proof before action</span>
        </Reveal>

        <div className={styles.grid}>
          <div className={styles.copy}>
            <Reveal delay={0.04} variant="fade">
              <p className={styles.eyebrow}>
                <span aria-hidden="true" />
                Code-enforced incident response
              </p>
            </Reveal>

            <Reveal delay={0.1} variant="hero">
              <h1 id="hero-title">
                Show your work.
                <span>Or don&apos;t act.</span>
              </h1>
            </Reveal>

            <Reveal delay={0.2} className={styles.statement}>
              <p className={styles.statementLabel}>Why Agent K</p>
              <p>
                An incident-response agent that investigates AI failures through
                observable telemetry. It can propose a cause — but can&apos;t
                publish one without evidence. It can&apost grant itself
                permission to act.
              </p>
            </Reveal>

            <Reveal delay={0.27} className={styles.actions}>
              <a className={styles.primaryAction} href="#live-demo">
                <Play aria-hidden="true" fill="currentColor" />
                Follow the incident
              </a>
              <a className={styles.secondaryAction} href="#laws">
                Read the enforcement model
                <ArrowDown aria-hidden="true" />
              </a>
            </Reveal>

            <Reveal delay={0.34} variant="fade">
              <dl className={styles.trustRail} aria-label="Core safeguards">
                {trustItems.map((item) => (
                  <div key={item.label}>
                    <dt>{item.label}</dt>
                    <dd>{item.value}</dd>
                  </div>
                ))}
              </dl>
            </Reveal>
          </div>

          <Reveal
            className={styles.visual}
            delay={0.16}
            amount={0.08}
            variant="side"
          >
            <IncidentSimulation />
          </Reveal>
        </div>
      </section>

      <Reveal amount={0.16} variant="fade">
        <InvestigationRibbon />
      </Reveal>
    </>
  );
}
