"use client";

import { useFrame } from "@react-three/fiber";
import {
	AdditiveBlending,
	CatmullRomCurve3,
	Color,
	Group,
	InstancedMesh,
	LineBasicMaterial,
	MathUtils,
	MeshBasicMaterial,
	Object3D,
	Vector3,
} from "three";
import { useMemo, useRef } from "react";

import { readNarrative } from "./sceneState";
import type { SceneQuality } from "./sceneState";

interface TelemetryStreamProps {
	quality: SceneQuality;
}

const PATH_COLORS = ["#3d9bff", "#8175ff", "#ff5b50"] as const;

export function TelemetryStream({ quality }: TelemetryStreamProps) {
	const pulseCount = quality === "high" ? 18 : 9;
	const groupRef = useRef<Group>(null);
	const lineMaterialRef = useRef<LineBasicMaterial>(null);
	const pulseMaterialRef = useRef<MeshBasicMaterial>(null);
	const pulsesRef = useRef<InstancedMesh>(null);
	const dummy = useMemo(() => new Object3D(), []);
	const curves = useMemo(
		() =>
			PATH_COLORS.map(
				(_, index) =>
					new CatmullRomCurve3([
						new Vector3(-6.5, (index - 1) * 1.25, index * 0.2),
						new Vector3(-3.8, (1 - index) * 0.8, -1 + index * 0.7),
						new Vector3(-1.7, (index - 1) * 0.5, 0.6 - index * 0.3),
						new Vector3(0, 0, 0),
					]),
			),
		[],
	);
	const linePositions = useMemo(() => {
		const segments = quality === "high" ? 64 : 32;
		const output = new Float32Array(curves.length * segments * 2 * 3);
		let offset = 0;
		curves.forEach((curve) => {
			for (let index = 0; index < segments; index += 1) {
				const from = curve.getPoint(index / segments);
				const to = curve.getPoint((index + 1) / segments);
				from.toArray(output, offset);
				to.toArray(output, offset + 3);
				offset += 6;
			}
		});
		return output;
	}, [curves, quality]);

	useFrame(({ clock }, delta) => {
		if (
			!groupRef.current ||
			!lineMaterialRef.current ||
			!pulseMaterialRef.current ||
			!pulsesRef.current
		)
			return;
		const narrative = readNarrative();
		const hero = narrative.chapters[0]?.weight ?? 0;
		const protocol = narrative.chapters[3]?.weight ?? 0;
		const proof = narrative.chapters[4]?.weight ?? 0;
		const visibility = Math.max(hero, protocol, proof * 0.8);
		const protocolProgress = narrative.chapters[3]?.progress ?? 0;

		for (let index = 0; index < pulseCount; index += 1) {
			const curve = curves[index % curves.length] ?? curves[0];
			if (!curve) continue;
			const travel =
				(clock.elapsedTime * (0.08 + protocol * 0.08) +
					index / pulseCount +
					protocolProgress * 0.18) %
				1;
			const point = curve.getPoint(travel);
			dummy.position.copy(point);
			dummy.scale.setScalar(0.055 + (index % 3) * 0.018);
			dummy.updateMatrix();
			pulsesRef.current.setMatrixAt(index, dummy.matrix);
		}
		pulsesRef.current.instanceMatrix.needsUpdate = true;
		groupRef.current.rotation.z = MathUtils.damp(
			groupRef.current.rotation.z,
			narrative.pointerY * 0.035,
			3,
			delta,
		);
		lineMaterialRef.current.opacity = MathUtils.damp(
			lineMaterialRef.current.opacity,
			visibility * (narrative.theme > 0.5 ? 0.32 : 0.17),
			4,
			delta,
		);
		pulseMaterialRef.current.opacity = MathUtils.damp(
			pulseMaterialRef.current.opacity,
			visibility * (narrative.theme > 0.5 ? 0.78 : 0.48),
			4,
			delta,
		);
	});

	return (
		<group ref={groupRef}>
			<lineSegments>
				<bufferGeometry>
					<bufferAttribute
						attach="attributes-position"
						args={[linePositions, 3]}
					/>
				</bufferGeometry>
				<lineBasicMaterial
					ref={lineMaterialRef}
					blending={AdditiveBlending}
					color={new Color("#5b8fff")}
					depthWrite={false}
					opacity={0}
					transparent
				/>
			</lineSegments>
			<instancedMesh ref={pulsesRef} args={[undefined, undefined, pulseCount]}>
				<sphereGeometry args={[1, 6, 6]} />
				<meshBasicMaterial
					ref={pulseMaterialRef}
					blending={AdditiveBlending}
					color="#8fc9ff"
					depthWrite={false}
					opacity={0}
					transparent
				/>
			</instancedMesh>
		</group>
	);
}
