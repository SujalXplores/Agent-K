"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";

import type { SceneQuality } from "./sceneState";
import { ScrollScene } from "./ScrollScene";
import styles from "./CinematicLayer.module.css";

const CinematicCanvas = dynamic(
	() => import("./CinematicCanvas").then((module) => module.CinematicCanvas),
	{ ssr: false },
);

interface NavigatorCapabilities extends Navigator {
	deviceMemory?: number;
}

export function CinematicLayer() {
	const [quality, setQuality] = useState<SceneQuality>("low");
	const [ready, setReady] = useState(false);

	useEffect(() => {
		const reduceMotion = window.matchMedia(
			"(prefers-reduced-motion: reduce)",
		).matches;
		const canvas = document.createElement("canvas");
		const hasWebGl = Boolean(
			canvas.getContext("webgl2") ?? canvas.getContext("webgl"),
		);
		if (reduceMotion || !hasWebGl) return;

		const capabilities = navigator as NavigatorCapabilities;
		const lowCapability =
			window.innerWidth < 820 ||
			navigator.hardwareConcurrency <= 4 ||
			(capabilities.deviceMemory !== undefined &&
				capabilities.deviceMemory <= 4);
		setQuality(lowCapability ? "low" : "high");

		const activate = () => setReady(true);
		const idleWindow = window as Window & {
			requestIdleCallback?: Window["requestIdleCallback"];
			cancelIdleCallback?: Window["cancelIdleCallback"];
		};
		if (idleWindow.requestIdleCallback) {
			const idleId = idleWindow.requestIdleCallback(activate, {
				timeout: 1200,
			});
			return () => idleWindow.cancelIdleCallback?.(idleId);
		}

		const timeoutId = globalThis.setTimeout(activate, 320);
		return () => globalThis.clearTimeout(timeoutId);
	}, []);

	return (
		<div className={styles.host} aria-hidden="true">
			<div className={styles.ambient} />
			{ready ? <CinematicCanvas quality={quality} /> : null}
			<ScrollScene enabled={ready} />
		</div>
	);
}
