"use client";

import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useEffect } from "react";

import {
	CHAPTER_SELECTORS,
	setChapterFrame,
	setNarrativeInput,
} from "./sceneState";

interface ScrollSceneProps {
	enabled: boolean;
}

export function ScrollScene({ enabled }: ScrollSceneProps) {
	useEffect(() => {
		if (!enabled) return;

		gsap.registerPlugin(ScrollTrigger);
		const triggers = CHAPTER_SELECTORS.flatMap((selector, index) => {
			const element = document.querySelector<HTMLElement>(selector);
			if (!element) return [];

			return [
				ScrollTrigger.create({
					trigger: element,
					start: index === 0 ? "top top" : "top bottom",
					end:
						index === CHAPTER_SELECTORS.length - 1
							? "bottom bottom"
							: "bottom top",
					onUpdate: ({ progress, getVelocity }) => {
						setChapterFrame(index, progress);
						setNarrativeInput({ scrollVelocity: getVelocity() });
					},
				}),
			];
		});

		const handlePointer = (event: PointerEvent) => {
			setNarrativeInput({
				pointerX: (event.clientX / window.innerWidth) * 2 - 1,
				pointerY: (event.clientY / window.innerHeight) * 2 - 1,
			});
		};

		const syncTheme = () => {
			setNarrativeInput({
				theme: document.documentElement.dataset.theme === "dark" ? 1 : 0,
			});
		};

		syncTheme();
		const themeObserver = new MutationObserver(syncTheme);
		themeObserver.observe(document.documentElement, {
			attributes: true,
			attributeFilter: ["data-theme"],
		});

		const updateScrollTrigger = () => ScrollTrigger.update();
		let connectedLenis = window.__lenis;
		const connectLenis = () => {
			connectedLenis?.off("scroll", updateScrollTrigger);
			connectedLenis = window.__lenis;
			connectedLenis?.on("scroll", updateScrollTrigger);
		};
		connectLenis();

		window.addEventListener("pointermove", handlePointer, { passive: true });
		window.addEventListener("agentk:lenis-ready", connectLenis);
		void document.fonts.ready.then(() => ScrollTrigger.refresh());
		ScrollTrigger.refresh();

		return () => {
			triggers.forEach((trigger) => trigger.kill());
			connectedLenis?.off("scroll", updateScrollTrigger);
			themeObserver.disconnect();
			window.removeEventListener("pointermove", handlePointer);
			window.removeEventListener("agentk:lenis-ready", connectLenis);
		};
	}, [enabled]);

	return null;
}
