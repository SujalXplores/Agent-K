"use client";

import { Canvas } from "@react-three/fiber";
import { AdaptiveDpr, PerformanceMonitor, Preload } from "@react-three/drei";
import { useState } from "react";

import { SceneManager } from "./SceneManager";
import type { SceneQuality } from "./sceneState";

interface CinematicCanvasProps {
	quality: SceneQuality;
}

export function CinematicCanvas({ quality }: CinematicCanvasProps) {
	const initialDpr = quality === "high" ? 1.35 : 0.9;
	const [dpr, setDpr] = useState(initialDpr);

	return (
		<Canvas
			camera={{ fov: 42, near: 0.1, far: 80, position: [0, 0, 10] }}
			dpr={dpr}
			flat
			frameloop="always"
			gl={{
				alpha: true,
				antialias: quality === "high",
				powerPreference: "high-performance",
			}}
			onCreated={({ gl }) => gl.setClearColor(0x000000, 0)}
			performance={{ min: 0.55 }}
		>
			<PerformanceMonitor
				flipflops={1}
				onDecline={() => setDpr(quality === "high" ? 1 : 0.75)}
				onIncline={() => setDpr(initialDpr)}
			/>
			<AdaptiveDpr />
			<SceneManager quality={quality} />
			<Preload all />
		</Canvas>
	);
}
