"use client";

import { useFrame, useThree } from "@react-three/fiber";
import { MathUtils, Vector3 } from "three";
import { useRef } from "react";

import { readNarrative } from "./sceneState";

const CAMERA_POSITIONS = [
	[0.8, 0.2, 10],
	[-0.7, 0.35, 9.2],
	[0, -0.15, 8.3],
	[1.35, 0.25, 8.8],
	[-0.45, 0.1, 7.8],
	[0.55, -0.25, 8.4],
	[0, 0, 7.4],
] as const;

export function CameraRig() {
	const { camera } = useThree();
	const lookAt = useRef(new Vector3());

	useFrame((_, delta) => {
		const narrative = readNarrative();
		let total = 0;
		let targetX = 0;
		let targetY = 0;
		let targetZ = 0;

		narrative.chapters.forEach((chapter, index) => {
			const position = CAMERA_POSITIONS[index] ?? CAMERA_POSITIONS[0];
			total += chapter.weight;
			targetX += position[0] * chapter.weight;
			targetY += position[1] * chapter.weight;
			targetZ += position[2] * chapter.weight;
		});

		const divisor = Math.max(total, 0.001);
		targetX = targetX / divisor + narrative.pointerX * 0.18;
		targetY = targetY / divisor - narrative.pointerY * 0.12;
		targetZ /= divisor;
		camera.position.x = MathUtils.damp(camera.position.x, targetX, 3.4, delta);
		camera.position.y = MathUtils.damp(camera.position.y, targetY, 3.4, delta);
		camera.position.z = MathUtils.damp(camera.position.z, targetZ, 3.1, delta);
		lookAt.current.x = MathUtils.damp(
			lookAt.current.x,
			narrative.pointerX * 0.14,
			4,
			delta,
		);
		lookAt.current.y = MathUtils.damp(
			lookAt.current.y,
			-narrative.pointerY * 0.08,
			4,
			delta,
		);
		camera.lookAt(lookAt.current);
	});

	return null;
}
