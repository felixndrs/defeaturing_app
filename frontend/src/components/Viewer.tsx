import { Suspense, useEffect, useMemo, useRef } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { OrbitControls, useGLTF, Grid, Html } from "@react-three/drei";
import * as THREE from "three";
import { geometryUrl } from "../api";
import type { FeatureChange } from "../types";

const BASE_COLOR = new THREE.Color("#8b93a1");
const HIGHLIGHT_COLOR = new THREE.Color("#f59e0b");

/**
 * One model, with the faces belonging to the selected feature painted in the
 * highlight colour. Each mesh gets its own material so colouring one face never
 * bleeds into another (and never mutates the cached glTF).
 */
function Model({
  modelId,
  position,
  highlightIds,
}: {
  modelId: string;
  position: [number, number, number];
  highlightIds: Set<string>;
}) {
  const { scene } = useGLTF(geometryUrl(modelId));

  const cloned = useMemo(() => {
    const copy = scene.clone(true);
    copy.traverse((obj) => {
      const mesh = obj as THREE.Mesh;
      if (mesh.isMesh) {
        mesh.material = new THREE.MeshStandardMaterial({
          color: BASE_COLOR.clone(),
          metalness: 0.1,
          roughness: 0.7,
          side: THREE.DoubleSide,
        });
      }
    });
    return copy;
  }, [scene]);

  useEffect(() => {
    cloned.traverse((obj) => {
      const mesh = obj as THREE.Mesh;
      if (!mesh.isMesh) return;
      const mat = mesh.material as THREE.MeshStandardMaterial;
      const on = highlightIds.has(mesh.name);
      mat.color.copy(on ? HIGHLIGHT_COLOR : BASE_COLOR);
      mat.emissive.copy(on ? HIGHLIGHT_COLOR : new THREE.Color("#000000"));
      mat.emissiveIntensity = on ? 0.4 : 0;
    });
  }, [cloned, highlightIds]);

  return <primitive object={cloned} position={position} />;
}

/** Re-centres the orbit target on the selected feature so both models frame it. */
function FocusTarget({
  controls,
  feature,
}: {
  controls: React.MutableRefObject<any>;
  feature: FeatureChange | null;
}) {
  useEffect(() => {
    if (!feature?.centroid || !controls.current) return;
    const [x, y, z] = feature.centroid;
    controls.current.target.set(x, y, z);
    controls.current.update();
  }, [feature, controls]);
  return null;
}

function Scene({
  originalId,
  defeaturedId,
  feature,
  gap,
}: {
  originalId: string;
  defeaturedId: string;
  feature: FeatureChange | null;
  gap: number;
}) {
  const controls = useRef<any>(null);
  const { camera } = useThree();

  useEffect(() => {
    camera.position.set(gap * 1.1, gap * 0.9, gap * 1.6);
  }, [camera, gap]);

  const originalHi = useMemo(
    () => new Set(feature?.geometry_refs.original_face_ids ?? []),
    [feature],
  );
  const defeaturedHi = useMemo(
    () => new Set(feature?.geometry_refs.defeatured_face_ids ?? []),
    [feature],
  );

  return (
    <>
      <ambientLight intensity={0.6} />
      <directionalLight position={[1, 2, 3]} intensity={1.1} />
      <directionalLight position={[-2, -1, -1]} intensity={0.4} />
      <Suspense fallback={<Html center>Lade Original…</Html>}>
        <Model modelId={originalId} position={[0, 0, 0]} highlightIds={originalHi} />
      </Suspense>
      <Suspense fallback={null}>
        <Model modelId={defeaturedId} position={[gap, 0, 0]} highlightIds={defeaturedHi} />
      </Suspense>
      <Grid
        position={[gap / 2, -0.01, 0]}
        args={[gap * 4, gap * 4]}
        cellColor="#1f2937"
        sectionColor="#374151"
        infiniteGrid
        fadeDistance={gap * 8}
      />
      <OrbitControls ref={controls} makeDefault target={[gap / 2, 0, 0]} />
      <FocusTarget controls={controls} feature={feature} />
    </>
  );
}

export function Viewer({
  originalId,
  defeaturedId,
  feature,
  gap = 80,
}: {
  originalId: string;
  defeaturedId: string;
  feature: FeatureChange | null;
  gap?: number;
}) {
  return (
    <div className="relative h-full w-full">
      <div className="pointer-events-none absolute left-3 top-2 z-10 text-xs font-medium text-gray-400">
        Original
      </div>
      <div className="pointer-events-none absolute right-3 top-2 z-10 text-xs font-medium text-gray-400">
        Defeatured
      </div>
      <Canvas camera={{ position: [gap, gap, gap * 1.6], fov: 45, near: 0.1, far: gap * 40 }}>
        <color attach="background" args={["#0b0f19"]} />
        <Scene
          originalId={originalId}
          defeaturedId={defeaturedId}
          feature={feature}
          gap={gap}
        />
      </Canvas>
    </div>
  );
}
