"use client";

import { useReducedMotion } from "motion/react";
import { useEffect } from "react";
import type { PropsWithChildren } from "react";

export function SmoothScroll({ children }: PropsWithChildren) {
	const reduceMotion = useReducedMotion();

	useEffect(() => {
		if (reduceMotion) return;

		const isCoarsePointer = window.matchMedia("(pointer: coarse)").matches;
		if (isCoarsePointer) return;

		let rafId = 0;
		let lenis: import("lenis").default | null = null;

		void import("lenis").then(({ default: Lenis }) => {
			lenis = new Lenis({
				duration: 1.1,
				easing: (t: number) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
				smoothWheel: true,
				wheelMultiplier: 1,
				touchMultiplier: 1.5,
				lerp: 0.1,
			});

			window.__lenis = lenis;
			window.dispatchEvent(new Event("agentk:lenis-ready"));

			const raf = (time: number) => {
				lenis?.raf(time);
				rafId = requestAnimationFrame(raf);
			};
			rafId = requestAnimationFrame(raf);
		});

		return () => {
			cancelAnimationFrame(rafId);
			lenis?.destroy();
			lenis = null;
			delete window.__lenis;
		};
	}, [reduceMotion]);

	return <>{children}</>;
}
