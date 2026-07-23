"use client";

import { useFrame } from "@react-three/fiber";
import {
	AdditiveBlending,
	BufferAttribute,
	Color,
	Group,
	MathUtils,
	PointsMaterial,
} from "three";
import { useMemo, useRef } from "react";

import { readNarrative } from "./sceneState";
import type { SceneQuality } from "./sceneState";

interface ParticleFieldProps {
	quality: SceneQuality;
}

const BLUE = new Color("#3994ff");
const VIOLET = new Color("#7a70ff");
const CORAL = new Color("#ff5b50");
const random = (seed: number): number => {
	const value = Math.sin(seed * 91.733) * 43758.5453;
	return value - Math.floor(value);
};

export function ParticleField({ quality }: ParticleFieldProps) {
	const count = quality === "high" ? 1100 : 460;
	const groupRef = useRef<Group>(null);
	const positionRef = useRef<BufferAttribute>(null);
	const materialRef = useRef<PointsMaterial>(null);
	const data = useMemo(() => {
		const positions = new Float32Array(count * 3);
		const colors = new Float32Array(count * 3);
		const phases = new Float32Array(count);
		const radii = new Float32Array(count);
		for (let index = 0; index < count; index += 1) {
			const phase = random(index + 1);
			phases[index] = phase;
			radii[index] = 0.7 + random(index + 19) * 2.6;
			const color = index % 17 === 0 ? CORAL : index % 3 === 0 ? VIOLET : BLUE;
			color.toArray(colors, index * 3);
			positions[index * 3] = (phase - 0.5) * 13;
		}
		return { positions, colors, phases, radii };
	}, [count]);

	useFrame(({ clock }, delta) => {
		if (!groupRef.current || !positionRef.current || !materialRef.current)
			return;
		const narrative = readNarrative();
		const hero = narrative.chapters[0]?.weight ?? 0;
		const problem = narrative.chapters[1]?.weight ?? 0;
		const protocol = narrative.chapters[3]?.weight ?? 0;
		const proof = narrative.chapters[4]?.weight ?? 0;
		const self = narrative.chapters[5]?.weight ?? 0;
		const cta = narrative.chapters[6]?.weight ?? 0;
		const visibility = Math.max(
			hero,
			problem * 0.7,
			protocol,
			proof,
			self * 0.75,
			cta,
		);
		const convergence = Math.max(proof * 0.82, cta * 0.94);
		const speed = 0.018 + protocol * 0.05 + proof * 0.03;

		for (let index = 0; index < count; index += 1) {
			const phase = data.phases[index] ?? 0;
			const radius = data.radii[index] ?? 1;
			const travel = (phase + clock.elapsedTime * speed) % 1;
			const angle = travel * Math.PI * 8 + phase * Math.PI * 2;
			const offset = index * 3;
			data.positions[offset] = MathUtils.lerp(
				(travel - 0.5) * 13,
				0,
				convergence,
			);
			data.positions[offset + 1] =
				Math.sin(angle) * radius * (1 - convergence * 0.78);
			data.positions[offset + 2] =
				Math.cos(angle) * radius * (1 - convergence * 0.78);
		}
		positionRef.current.needsUpdate = true;
		groupRef.current.rotation.x = MathUtils.damp(
			groupRef.current.rotation.x,
			narrative.pointerY * 0.08,
			3,
			delta,
		);
		materialRef.current.opacity = MathUtils.damp(
			materialRef.current.opacity,
			visibility * MathUtils.lerp(0.24, 0.5, narrative.theme),
			4,
			delta,
		);
	});

	return (
		<group ref={groupRef}>
			<points>
				<bufferGeometry>
					<bufferAttribute
						ref={positionRef}
						attach="attributes-position"
						args={[data.positions, 3]}
					/>
					<bufferAttribute attach="attributes-color" args={[data.colors, 3]} />
				</bufferGeometry>
				<pointsMaterial
					ref={materialRef}
					blending={AdditiveBlending}
					depthWrite={false}
					opacity={0}
					size={quality === "high" ? 0.038 : 0.052}
					sizeAttenuation
					transparent
					vertexColors
				/>
			</points>
		</group>
	);
}
