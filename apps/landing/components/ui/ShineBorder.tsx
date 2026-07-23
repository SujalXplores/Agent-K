"use client";

import { m, useReducedMotion } from "motion/react";

import styles from "./ShineBorder.module.css";

export type ShineTone =
	| "evidence"
	| "govern"
	| "observe"
	| "policy"
	| "reason"
	| "signal"
	| "telemetry"
	| "verified";

interface ShineBorderProps {
	delay?: number;
	reverse?: boolean;
	tone?: ShineTone;
}

export function ShineBorder({
	delay = 0,
	reverse = false,
	tone = "evidence",
}: ShineBorderProps) {
	const reduceMotion = useReducedMotion();
	const rotation = reverse ? -360 : 360;

	return (
		<span className={`${styles.border} ${styles[tone]}`} aria-hidden="true">
			<m.span
				className={styles.shine}
				initial={false}
				animate={{ rotate: reduceMotion ? 0 : rotation }}
				transition={
					reduceMotion
						? { duration: 0 }
						: { delay, duration: 14, ease: "linear", repeat: Infinity }
				}
			/>
		</span>
	);
}
