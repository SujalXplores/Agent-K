import { ArrowUpRight, ShieldCheck } from "lucide-react";

import { Reveal } from "../motion/Reveal";
import { ReplayJumpButton } from "../ui/ReplayJumpButton";
import { ShineBorder } from "../ui/ShineBorder";
import styles from "./FinalCta.module.css";

export function FinalCta() {
	return (
		<section
			className={styles.section}
			id="final-cta"
			aria-labelledby="cta-title"
		>
			<ShineBorder tone="verified" />
			<div className={styles.coordinates} aria-hidden="true">
				<span>37.7749 N</span>
				<span>Case / K-2026</span>
				<span>122.4194 W</span>
			</div>
			<div className={styles.mark} aria-hidden="true">
				K
			</div>
			<div className={styles.content}>
				<Reveal>
					<span className={styles.kicker}>
						<ShieldCheck aria-hidden="true" /> Proof before action. Always.
					</span>
				</Reveal>
				<Reveal delay={0.07} variant="hero">
					<h2 id="cta-title">Bring receipts to the pager.</h2>
				</Reveal>
				<Reveal delay={0.13}>
					<p>
						Watch an incident move from noisy signal to an evidence-backed,
						policy-gated, fully auditable outcome.
					</p>
				</Reveal>
				<Reveal className={styles.actions} delay={0.18}>
					<ReplayJumpButton className={styles.replayButton} />
					<a className={styles.safeguardsLink} href="#laws">
						Explore the safeguards
						<ArrowUpRight aria-hidden="true" />
					</a>
				</Reveal>
			</div>
		</section>
	);
}
