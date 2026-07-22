import {
  Activity,
  CircleDollarSign,
  Gauge,
  Quote,
  Repeat2,
  ScanEye,
} from 'lucide-react';

import { Reveal } from '../motion/Reveal';
import { SectionIntro } from '../ui/SectionIntro';
import styles from './Problem.module.css';

const failureSignals = [
  {
    label: 'Latency',
    value: '+184%',
    detail: 'Responses degrade',
    icon: Gauge,
    tone: 'coral',
  },
  {
    label: 'Cost',
    value: 'Runaway',
    detail: 'Budget accelerates',
    icon: CircleDollarSign,
    tone: 'violet',
  },
  {
    label: 'Quality',
    value: 'Drifting',
    detail: 'Answers look valid',
    icon: ScanEye,
    tone: 'blue',
  },
  {
    label: 'Loops',
    value: 'Repeating',
    detail: 'Tools cycle silently',
    icon: Repeat2,
    tone: 'acid',
  },
] as const;

export function Problem() {
  return (
    <section
      className={styles.section}
      id="problem"
      aria-labelledby="problem-title"
    >
      <Reveal>
        <SectionIntro
          number="01"
          label="The blind spot"
          title={
            <span id="problem-title">
              AI failures rarely arrive as a red light.
            </span>
          }
          description={
            <>
              They get slower. More expensive. Less accurate. They repeat
              themselves without throwing a conventional error. The story is
              scattered across traces, logs, metrics, and deployments.
            </>
          }
        />
      </Reveal>

      <div className={styles.grid}>
        <Reveal className={styles.argument} delay={0.06}>
          <div className={styles.argumentIndex}>Observation / 01</div>
          <blockquote>
            <Quote aria-hidden="true" />
            <p>Faster guesses are still guesses.</p>
            <cite>Agent K starts with the evidence.</cite>
          </blockquote>
          <p className={styles.argumentCopy}>
            Conventional alerts can tell you a threshold moved. They can&apos;t
            prove why it moved, whether a proposed action is safe, or whether
            recovery held. Agent K treats those as separate questions with
            separate evidence.
          </p>
        </Reveal>

        <div className={styles.signalBoard}>
          <Reveal className={styles.boardHeader} delay={0.1} variant="fade">
            <span>Failure signal register</span>
            <span>Illustrative</span>
          </Reveal>
          <div className={styles.signalGrid}>
            {failureSignals.map(
              ({ label, value, detail, icon: Icon, tone }, index) => (
                <Reveal
                  as="article"
                  className={styles[tone]}
                  delay={0.05 + index * 0.06}
                  key={label}
                  variant="panel"
                >
                  <Icon aria-hidden="true" />
                  <span>{label}</span>
                  <strong>{value}</strong>
                  <small>{detail}</small>
                </Reveal>
              ),
            )}
          </div>
          <Reveal className={styles.boardFooter} delay={0.12} variant="fade">
            <Activity aria-hidden="true" />
            <p>
              <span>Failure is broader than error.</span>
              Observe the system before explaining it.
            </p>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
