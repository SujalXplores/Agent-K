"use client";

import type { SceneQuality } from "./sceneState";
import {
	AICore,
	CameraRig,
	EvidenceGate,
	NetworkGraph,
	ParticleField,
	TelemetryStream,
} from "./sceneComponents";

interface SceneManagerProps {
	quality: SceneQuality;
}

export function SceneManager({ quality }: SceneManagerProps) {
	return (
		<>
			<fog attach="fog" args={["#090b12", 10, 24]} />
			<CameraRig />
			<group position={[1.65, 0, 0]}>
				<ParticleField quality={quality} />
				<TelemetryStream quality={quality} />
				<NetworkGraph quality={quality} />
				<AICore />
				<EvidenceGate />
			</group>
		</>
	);
}
