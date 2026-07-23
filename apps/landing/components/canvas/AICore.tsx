"use client";

import { useFrame } from "@react-three/fiber";
import {
	AdditiveBlending,
	Color,
	Group,
	MathUtils,
	MeshBasicMaterial,
} from "three";
import { useRef } from "react";

import { readNarrative } from "./sceneState";

const LIGHT_COLOR = new Color("#3f6fca");
const DARK_COLOR = new Color("#78b9ff");

export function AICore() {
	const groupRef = useRef<Group>(null);
	const materialRef = useRef<MeshBasicMaterial>(null);
	const color = useRef(new Color());

	useFrame(({ clock }, delta) => {
		if (!groupRef.current || !materialRef.current) return;
		const narrative = readNarrative();
		const proof = narrative.chapters[4]?.weight ?? 0;
		const self = narrative.chapters[5]?.weight ?? 0;
		const cta = narrative.chapters[6]?.weight ?? 0;
		const pulse = 1 + Math.sin(clock.elapsedTime * 1.35) * 0.035;
		const targetScale = pulse + proof * 0.12 + cta * 0.18;

		groupRef.current.rotation.x += delta * (0.06 + self * 0.08);
		groupRef.current.rotation.y += delta * (0.11 + proof * 0.09);
		groupRef.current.scale.setScalar(
			MathUtils.damp(groupRef.current.scale.x, targetScale, 4, delta),
		);
		color.current.lerpColors(LIGHT_COLOR, DARK_COLOR, narrative.theme);
		materialRef.current.color.copy(color.current);
		materialRef.current.opacity = MathUtils.damp(
			materialRef.current.opacity,
			0.18 + proof * 0.26 + self * 0.2 + cta * 0.32,
			4,
			delta,
		);
	});

	return (
		<group ref={groupRef}>
			<mesh>
				<icosahedronGeometry args={[1.12, 3]} />
				<meshBasicMaterial
					ref={materialRef}
					blending={AdditiveBlending}
					depthWrite={false}
					transparent
					wireframe
				/>
			</mesh>
		</group>
	);
}
