"use client";

import { useFrame } from "@react-three/fiber";
import {
	Group,
	InstancedMesh,
	LineBasicMaterial,
	MathUtils,
	MeshBasicMaterial,
	Object3D,
	Vector3,
} from "three";
import { useMemo, useRef } from "react";

import {
	NETWORK_COLORS,
	NETWORK_EDGES,
	NODE_POSITIONS,
	ROOT_NODE,
} from "./networkData";
import { readNarrative } from "./sceneState";
import type { SceneQuality } from "./sceneState";

interface NetworkGraphProps {
	quality: SceneQuality;
}

export function NetworkGraph({ quality }: NetworkGraphProps) {
	const groupRef = useRef<Group>(null);
	const nodesRef = useRef<InstancedMesh>(null);
	const nodeMaterialRef = useRef<MeshBasicMaterial>(null);
	const lineMaterialRef = useRef<LineBasicMaterial>(null);
	const dummy = useMemo(() => new Object3D(), []);
	const vectors = useMemo(
		() => NODE_POSITIONS.map((position) => new Vector3(...position)),
		[],
	);

	const linePositions = useMemo(() => {
		const output = new Float32Array(NETWORK_EDGES.length * 6);
		NETWORK_EDGES.forEach(([fromIndex, toIndex], index) => {
			vectors[fromIndex]?.toArray(output, index * 6);
			vectors[toIndex]?.toArray(output, index * 6 + 3);
		});
		return output;
	}, [vectors]);

	useFrame(({ clock }, delta) => {
		if (
			!groupRef.current ||
			!nodesRef.current ||
			!nodeMaterialRef.current ||
			!lineMaterialRef.current
		)
			return;
		const narrative = readNarrative();
		const problem = narrative.chapters[1]?.weight ?? 0;
		const proof = narrative.chapters[4]?.weight ?? 0;
		const visibility = Math.max(problem, proof * 0.92);

		vectors.forEach((position, index) => {
			const wave = Math.max(
				0,
				Math.sin(
					clock.elapsedTime * 2.2 -
						position.distanceTo(vectors[ROOT_NODE] ?? position) * 1.6,
				),
			);
			const isRoot = index === ROOT_NODE;
			dummy.position.copy(position);
			dummy.scale.setScalar(
				0.12 + wave * problem * 0.08 + (isRoot ? proof * 0.12 : 0),
			);
			dummy.updateMatrix();
			nodesRef.current?.setMatrixAt(index, dummy.matrix);
			const color = isRoot
				? proof > problem
					? NETWORK_COLORS.green
					: NETWORK_COLORS.coral
				: NETWORK_COLORS.blue.clone().lerp(NETWORK_COLORS.dim, proof * 0.75);
			nodesRef.current?.setColorAt(index, color);
		});
		nodesRef.current.instanceMatrix.needsUpdate = true;
		if (nodesRef.current.instanceColor)
			nodesRef.current.instanceColor.needsUpdate = true;
		groupRef.current.rotation.y = MathUtils.damp(
			groupRef.current.rotation.y,
			narrative.pointerX * 0.1 + proof * 0.2,
			3,
			delta,
		);
		nodeMaterialRef.current.opacity = MathUtils.damp(
			nodeMaterialRef.current.opacity,
			visibility * (narrative.theme > 0.5 ? 0.88 : 0.55),
			4,
			delta,
		);
		lineMaterialRef.current.opacity = MathUtils.damp(
			lineMaterialRef.current.opacity,
			visibility * (narrative.theme > 0.5 ? 0.34 : 0.16),
			4,
			delta,
		);
	});

	return (
		<group ref={groupRef} scale={quality === "high" ? 1 : 0.92}>
			<lineSegments>
				<bufferGeometry>
					<bufferAttribute
						attach="attributes-position"
						args={[linePositions, 3]}
					/>
				</bufferGeometry>
				<lineBasicMaterial
					ref={lineMaterialRef}
					color="#608dce"
					opacity={0}
					transparent
				/>
			</lineSegments>
			<instancedMesh
				ref={nodesRef}
				args={[undefined, undefined, vectors.length]}
			>
				<icosahedronGeometry args={[1, quality === "high" ? 1 : 0]} />
				<meshBasicMaterial
					ref={nodeMaterialRef}
					opacity={0}
					transparent
					vertexColors
				/>
			</instancedMesh>
		</group>
	);
}
