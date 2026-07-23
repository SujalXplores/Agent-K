import { ArrowRight, Check, ShieldCheck } from "lucide-react";

import {
	evaluationMetrics,
	illustrativeQuery,
	policyChecks,
	proofEvidence,
} from "../../data/content";
import { Reveal } from "../motion/Reveal";
import { CopyQueryButton } from "../ui/CopyQueryButton";
import { SectionIntro } from "../ui/SectionIntro";
import { ShineBorder } from "../ui/ShineBorder";
import styles from "./Proof.module.css";

const recoveryBars = [
	84, 88, 82, 79, 72, 58, 43, 29, 20, 16, 13, 12, 11, 10,
] as const;

export function Proof() {
	return (
		<section
			className={styles.section}
			id="proof"
			aria-labelledby="proof-title"
		>
			<Reveal>
				<SectionIntro
					number="04"
					label="Inspectable by design"
					title={
						<span id="proof-title">One incident. Every decision visible.</span>
					}
					description={
						<>
							The report doesn&apos;t ask for trust. It exposes the claim,
							supporting query, policy boundary, and what happened after the
							decision.
						</>
					}
				/>
			</Reveal>

			<Reveal className={styles.boardReveal} amount={0.06} variant="panel">
				<article
					className={styles.board}
					aria-label="Illustrative Agent K incident report"
				>
					<ShineBorder tone="evidence" />
					<header className={styles.boardHeader}>
						<div>
							<span className={styles.sampleBadge}>Illustrative packet</span>
							<h3>Incident INC-042</h3>
							<p>Prompt-regression controlled scenario</p>
						</div>
						<div className={styles.completeStatus}>
							<Check aria-hidden="true" />
							Investigation complete
						</div>
					</header>

					<div className={styles.auditGrid}>
						<section
							className={styles.claimPanel}
							aria-labelledby="claim-title"
						>
							<span className={styles.microLabel} id="claim-title">
								Evidence-backed claim
							</span>
							<blockquote>
								Prompt template v2 caused the increase in failed support
								answers.
							</blockquote>
							<div className={styles.confidenceRow}>
								<div
									className={styles.confidenceDisc}
									aria-label="94 percent recalibrated confidence"
								>
									<span>
										94<small>%</small>
									</span>
								</div>
								<div>
									<span>Recalibrated confidence</span>
									<strong>Strong deployment correlation</strong>
								</div>
							</div>
							<div className={styles.queryBox}>
								<div>
									<span>Query / 02</span>
									<CopyQueryButton />
								</div>
								<code>{illustrativeQuery}</code>
							</div>
						</section>

						<section
							className={styles.evidencePanel}
							aria-labelledby="evidence-title"
						>
							<span className={styles.microLabel} id="evidence-title">
								Attached evidence
							</span>
							<ul>
								{proofEvidence.map((item) => (
									<li key={item.type}>
										<div className={styles.evidenceRecord}>
											<span className={styles.evidenceType}>{item.type}</span>
											<span>
												<strong>{item.title}</strong>
												<small>{item.detail}</small>
											</span>
										</div>
									</li>
								))}
							</ul>
							<div className={styles.resolved}>
								<Check aria-hidden="true" />3 evidence records attached
							</div>
						</section>

						<section
							className={styles.policyPanel}
							aria-labelledby="policy-title"
						>
							<div className={styles.panelTitleRow}>
								<span className={styles.microLabel} id="policy-title">
									Deterministic policy gate
								</span>
								<span className={styles.verdict}>Allow</span>
							</div>
							<ul className={styles.policyList}>
								{policyChecks.map((item) => (
									<li key={item}>
										<span>{item}</span>
										<Check aria-hidden="true" />
									</li>
								))}
							</ul>
							<div className={styles.actionRecord}>
								<ShieldCheck aria-hidden="true" />
								<span>
									<small>Authorized action</small>
									<strong>
										v2 <ArrowRight aria-hidden="true" /> v1
									</strong>
									<small>rollback / only permitted action</small>
								</span>
							</div>
						</section>

						<section
							className={styles.verificationPanel}
							aria-labelledby="verification-title"
						>
							<div className={styles.verificationCopy}>
								<span className={styles.microLabel} id="verification-title">
									Post-action verification
								</span>
								<strong>Recovery observed</strong>
								<p>
									Error rate returned beneath the controlled scenario threshold
									after rollback.
								</p>
							</div>
							<div
								className={styles.recoveryChart}
								role="img"
								aria-label="Illustrative error rate declining from 8.4 percent to 1.1 percent after rollback"
							>
								<div className={styles.chartScale} aria-hidden="true">
									<span>8.4%</span>
									<span>1.1%</span>
								</div>
								<div className={styles.rollbackMarker} aria-hidden="true">
									<span>rollback</span>
								</div>
								<div className={styles.recoveryBars} aria-hidden="true">
									{recoveryBars.map((height, index) => (
										<i
											key={`${height}-${index}`}
											style={{ height: `${height}%` }}
										/>
									))}
								</div>
							</div>
						</section>
					</div>
				</article>
			</Reveal>

			<Reveal className={styles.contract}>
				<ShineBorder delay={2.4} tone="verified" />
				<div className={styles.contractIntro}>
					<span>The evaluation contract</span>
					<h3>Targets, not trophies.</h3>
					<p>
						Agent K reports controlled results honestly. These are standards the
						build must prove, not claims of production readiness.
					</p>
				</div>
				<dl>
					{evaluationMetrics.map((metric) => (
						<div key={metric.label}>
							<dt>{metric.value}</dt>
							<dd>
								{metric.label}
								<span>{metric.note}</span>
							</dd>
						</div>
					))}
				</dl>
			</Reveal>
		</section>
	);
}
