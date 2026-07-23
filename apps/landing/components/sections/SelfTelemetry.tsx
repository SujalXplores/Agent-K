import { CircleDollarSign, Gauge, RefreshCw, ShieldCheck } from "lucide-react";

import { Reveal } from "../motion/Reveal";
import { SectionIntro } from "../ui/SectionIntro";
import { ShineBorder } from "../ui/ShineBorder";
import styles from "./SelfTelemetry.module.css";

const activityBars = [26, 42, 35, 67, 51, 84, 63, 92, 69, 43, 29, 17] as const;

export function SelfTelemetry() {
	return (
		<section
			className={styles.section}
			id="self-telemetry"
			aria-labelledby="self-title"
		>
			<div className={styles.shell}>
				<ShineBorder tone="telemetry" />
				<div className={styles.copy}>
					<Reveal>
						<SectionIntro
							number="05"
							label="The observer, observed"
							title={
								<span id="self-title">
									Even the investigator leaves a trace.
								</span>
							}
							description={
								<>
									Every query, token, repeat, cost, confidence shift, and policy
									verdict is emitted as telemetry. If Agent K loops or exceeds
									budget, code stops it.
								</>
							}
						/>
					</Reveal>
					<div className={styles.watchdogs}>
						<Reveal delay={0.06}>
							<article>
								<RefreshCw aria-hidden="true" />
								<span>
									<strong>Loop breaker</strong>
									<small>
										Repeated queries trigger a stop and human escalation.
									</small>
								</span>
							</article>
						</Reveal>
						<Reveal delay={0.1}>
							<article>
								<CircleDollarSign aria-hidden="true" />
								<span>
									<strong>Cost watchdog</strong>
									<small>
										Budget exhaustion ends the run before it can drift.
									</small>
								</span>
							</article>
						</Reveal>
					</div>
				</div>

				<Reveal
					className={styles.dashboardReveal}
					delay={0.08}
					amount={0.1}
					variant="side"
				>
					<article
						className={styles.dashboard}
						aria-label="Illustrative Agent K self-observability dashboard"
					>
						<header>
							<div>
								<span>Agent health</span>
								<strong>Run / INC-042</strong>
							</div>
							<span className={styles.healthy}>
								<ShieldCheck aria-hidden="true" /> Within budget
							</span>
						</header>
						<dl className={styles.healthMetrics}>
							<div>
								<dt>Duration</dt>
								<dd>01:42</dd>
								<span>min:sec</span>
							</div>
							<div>
								<dt>Queries</dt>
								<dd>08</dd>
								<span>0 repeats</span>
							</div>
							<div>
								<dt>Hypotheses</dt>
								<dd>03</dd>
								<span>1 supported</span>
							</div>
						</dl>
						<div className={styles.activityChart}>
							<div>
								<span>Investigation activity</span>
								<span>illustrative</span>
							</div>
							<div className={styles.barField} aria-hidden="true">
								{activityBars.map((height, index) => (
									<i
										key={`${height}-${index}`}
										style={{ height: `${height}%` }}
									/>
								))}
							</div>
							<Gauge className={styles.chartIcon} aria-hidden="true" />
						</div>
						<div className={styles.log}>
							<span>10:04:18</span>
							<span>policy.verdict</span>
							<strong>ALLOW</strong>
							<span>10:05:02</span>
							<span>rollback.verify</span>
							<strong>PASS</strong>
							<span>10:05:04</span>
							<span>report.sealed</span>
							<strong>DONE</strong>
						</div>
					</article>
				</Reveal>
			</div>
		</section>
	);
}
