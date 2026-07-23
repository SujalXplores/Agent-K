"use client";

import { Activity, Check, SearchCheck, ShieldCheck } from "lucide-react";
import { m, useReducedMotion, useScroll, useTransform } from "motion/react";
import { useRef } from "react";

import { laws } from "../../data/content";
import { SectionIntro } from "../ui/SectionIntro";
import { ShineBorder } from "../ui/ShineBorder";
import styles from "./Laws.module.css";

const lawIcons = {
	evidence: SearchCheck,
	policy: ShieldCheck,
	telemetry: Activity,
} as const;

export function Laws() {
	const sectionRef = useRef<HTMLElement>(null);
	const reduceMotion = useReducedMotion();
	const { scrollYProgress } = useScroll({
		target: sectionRef,
		offset: ["start end", "end start"],
	});

	// Background glow drifts as you scroll through the section
	const glowX = useTransform(scrollYProgress, [0, 1], ["-10%", "30%"]);
	const glowOpacity = useTransform(
		scrollYProgress,
		[0, 0.4, 0.8, 1],
		[0, 0.7, 0.7, 0],
	);

	// Per-card parallax: each card rises and settles at a different scroll point
	const cardY0 = useTransform(scrollYProgress, [0.05, 0.35], [60, 0]);
	const cardY1 = useTransform(scrollYProgress, [0.15, 0.5], [80, 0]);
	const cardY2 = useTransform(scrollYProgress, [0.28, 0.65], [100, 0]);
	const cardTransforms = [cardY0, cardY1, cardY2];

	// Per-card ghost number opacity
	const numOpacity0 = useTransform(scrollYProgress, [0.1, 0.3], [0, 0.06]);
	const numOpacity1 = useTransform(scrollYProgress, [0.22, 0.42], [0, 0.06]);
	const numOpacity2 = useTransform(scrollYProgress, [0.34, 0.54], [0, 0.06]);
	const numOpacities = [numOpacity0, numOpacity1, numOpacity2];

	// Header parallax — drifts upward slightly slower than scroll
	const headerY = useTransform(scrollYProgress, [0, 0.3], [40, 0]);
	const headerOpacity = useTransform(
		scrollYProgress,
		[0, 0.15, 0.3],
		[0.4, 1, 1],
	);

	return (
		<section
			className={styles.section}
			id="laws"
			aria-labelledby="laws-title"
			ref={sectionRef}
		>
			<m.div
				className={styles.glow}
				aria-hidden="true"
				{...(reduceMotion ? {} : { style: { x: glowX, opacity: glowOpacity } })}
			/>
			<div className={styles.inner}>
				<m.div
					{...(reduceMotion
						? {}
						: { style: { y: headerY, opacity: headerOpacity } })}
				>
					<SectionIntro
						inverse
						number="02"
						label="Code-enforced trust"
						title={
							<span id="laws-title">
								Trust isn&apos;t a prompt. It&apos;s an architecture.
							</span>
						}
						description={
							<>
								Three non-negotiable laws sit between the model and the world.
								Enforced by software, not requested with polite wording.
							</>
						}
					/>
				</m.div>

				<div className={styles.cards}>
					{laws.map((law, index) => {
						const LawIcon = lawIcons[law.key];
						return (
							<m.article
								className={`${styles.card} ${styles[law.key]}`}
								key={law.number}
								{...(reduceMotion
									? {}
									: { style: { y: cardTransforms[index] ?? cardY0 } })}
							>
								<ShineBorder
									delay={index * 1.4}
									reverse={index % 2 === 1}
									tone={law.key}
								/>
								<div className={styles.cardTop}>
									<span>{law.number} / 03</span>
									<span>{law.label}</span>
								</div>
								<m.div
									className={styles.iconBox}
									initial={false}
									{...(reduceMotion
										? {}
										: { whileHover: { scale: 1.06, rotate: -3 } })}
									transition={{ type: "spring", stiffness: 400, damping: 18 }}
								>
									<LawIcon aria-hidden="true" />
								</m.div>
								<h3>{law.title}</h3>
								<p>{law.description}</p>
								<ul>
									{law.checks.map(([label, value]) => (
										<li key={label}>
											<Check aria-hidden="true" />
											<span>{label}</span>
											<strong>{value}</strong>
										</li>
									))}
								</ul>
								<m.span
									className={styles.cardNumber}
									aria-hidden="true"
									initial={false}
									{...(reduceMotion
										? {}
										: { style: { opacity: numOpacities[index] } })}
								>
									{law.number}
								</m.span>
							</m.article>
						);
					})}
				</div>
			</div>
		</section>
	);
}
