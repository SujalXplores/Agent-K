"use client";

import { useFrame } from "@react-three/fiber";
import {
	AdditiveBlending,
	Color,
	InstancedMesh,
	MathUtils,
	Mesh,
	MeshBasicMaterial,
	Object3D,
} from "three";
import { useMemo, useRef } from "react";

import { readNarrative } from "./sceneState";

const RING_COLORS = [
	new Color("#3f9cff"),
	new Color("#8175ff"),
	new Color("#ff5b50"),
] as const;
const GREEN = new Color("#50df82");

export function EvidenceGate() {
	const ringsRef = useRef<InstancedMesh>(null);
	const ringMaterialRef = useRef<MeshBasicMaterial>(null);
	const recoveryRef = useRef<Mesh>(null);
	const recoveryMaterialRef = useRef<MeshBasicMaterial>(null);
	const dummy = useMemo(() => new Object3D(), []);

	useFrame(({ clock }, delta) => {
		if (
			!ringsRef.current ||
			!ringMaterialRef.current ||
			!recoveryRef.current ||
			!recoveryMaterialRef.current
		)
			return;

		const narrative = readNarrative();
		const laws = narrative.chapters[2]?.weight ?? 0;
		const protocol = narrative.chapters[3]?.weight ?? 0;
		const proof = narrative.chapters[4]?.weight ?? 0;
		const cta = narrative.chapters[6]?.weight ?? 0;
		const assembly = Math.max(laws, protocol * 0.55, proof);

		for (let index = 0; index < 3; index += 1) {
			const spread = (1 - assembly) * (3.4 + index * 0.7);
			dummy.position.set((index - 1) * spread, 0, 0);
			dummy.rotation.set(
				Math.PI / 2 + index * 0.7 + clock.elapsedTime * 0.04,
				index * 0.8 + clock.elapsedTime * 0.06,
				index * 0.55,
			);
			dummy.scale.setScalar(1 + index * 0.22);
			dummy.updateMatrix();
			ringsRef.current.setMatrixAt(index, dummy.matrix);
			ringsRef.current.setColorAt(index, RING_COLORS[index] ?? RING_COLORS[0]);
		}
		ringsRef.current.instanceMatrix.needsUpdate = true;
		if (ringsRef.current.instanceColor)
			ringsRef.current.instanceColor.needsUpdate = true;

		ringMaterialRef.current.opacity = MathUtils.damp(
			ringMaterialRef.current.opacity,
			assembly * (narrative.theme > 0.5 ? 0.52 : 0.28),
			4,
			delta,
		);

		const recovery = Math.max(proof, cta);
		const wave = (clock.elapsedTime * 0.22) % 1;
		recoveryRef.current.scale.setScalar(1.4 + wave * 4.2);
		recoveryMaterialRef.current.color.copy(GREEN);
		recoveryMaterialRef.current.opacity = MathUtils.damp(
			recoveryMaterialRef.current.opacity,
			recovery * (1 - wave) * (narrative.theme > 0.5 ? 0.34 : 0.18),
			5,
			delta,
		);
	});

	return (
		<group>
			<instancedMesh ref={ringsRef} args={[undefined, undefined, 3]}>
				<torusGeometry args={[1.7, 0.025, 6, 96]} />
				<meshBasicMaterial
					ref={ringMaterialRef}
					blending={AdditiveBlending}
					depthWrite={false}
					opacity={0}
					transparent
					vertexColors
				/>
			</instancedMesh>
			<mesh ref={recoveryRef} rotation={[Math.PI / 2, 0, 0]}>
				<ringGeometry args={[0.96, 1, 96]} />
				<meshBasicMaterial
					ref={recoveryMaterialRef}
					blending={AdditiveBlending}
					depthWrite={false}
					opacity={0}
					transparent
				/>
			</mesh>
		</group>
	);
}
