import {
  ArrowDown,
  BellRing,
  ClipboardCheck,
  Database,
  GitCompareArrows,
  ShieldCheck,
} from 'lucide-react';

import { protocolSteps } from '../../data/content';
import { Reveal } from '../motion/Reveal';
import { SectionIntro } from '../ui/SectionIntro';
import styles from './Protocol.module.css';

const protocolIcons = {
  signal: BellRing,
  observe: Database,
  reason: GitCompareArrows,
  govern: ShieldCheck,
  verify: ClipboardCheck,
} as const;

export function Protocol() {
  return (
    <section
      className={styles.section}
      id="protocol"
      aria-labelledby="protocol-title"
    >
      <div className={styles.layout}>
        <div className={styles.stickyIntro}>
          <Reveal>
            <SectionIntro
              number="03"
              label="The protocol"
              title={
                <span id="protocol-title">
                  From pager noise to a provable answer.
                </span>
              }
              description={
                <>
                  One continuous chain of custody carries an incident from first
                  signal to final report. Every handoff is inspectable.
                </>
              }
            />
          </Reveal>
          <Reveal delay={0.08}>
            <a className={styles.proofLink} href="#proof">
              Inspect the evidence packet
              <ArrowDown aria-hidden="true" />
            </a>
          </Reveal>
        </div>

        <ol className={styles.steps}>
          {protocolSteps.map((step, index) => {
            const StepIcon = protocolIcons[step.key];
            return (
              <Reveal delay={index * 0.04} key={step.number} variant="panel">
                <li className={`${styles.step} ${styles[step.key]}`}>
                  <div className={styles.stepIndex}>
                    <span>{step.number}</span>
                    <small>/ 05</small>
                  </div>
                  <div className={styles.stepBody}>
                    <span className={styles.stepTag}>{step.label}</span>
                    <h3>{step.title}</h3>
                    <p>{step.description}</p>
                  </div>
                  <div className={styles.stepIcon} aria-hidden="true">
                    <StepIcon />
                    <span>{step.number}</span>
                  </div>
                </li>
              </Reveal>
            );
          })}
        </ol>
      </div>
    </section>
  );
}
