import { Suspense, useEffect, useMemo, useRef } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { OrbitControls, useGLTF, Grid, Html, Text } from "@react-three/drei";
import * as THREE from "three";
import { geometryUrl } from "../api";
import type { FeatureChange } from "../types";

const BASE_COLOR = new THREE.Color("#9aa3b0");
const HIGHLIGHT_COLOR = new THREE.Color("#f59e0b");
const EDGE_COLOR = new THREE.Color("#3f4756");
// Dihedral angle (degrees) above which an edge is drawn -- keeps rounded
// fillets smooth while still outlining every real feature boundary.
const EDGE_THRESHOLD_DEG = 20;

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
        // Crisp CAD-style edge lines on top of the shaded face, so feature
        // boundaries (fillet start, hole rim, ...) stay legible without
        // relying on lighting gradients alone.
        const edges = new THREE.LineSegments(
          new THREE.EdgesGeometry(mesh.geometry, EDGE_THRESHOLD_DEG),
          new THREE.LineBasicMaterial({ color: EDGE_COLOR }),
        );
        edges.name = "__edges";
        mesh.add(edges);
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

  // "Imprint" labels lying flat on the grid under each model. Unlike a fixed
  // screen-space overlay, these are part of the 3D scene: they rotate with
  // the camera and always stay under their model, so orbiting never breaks
  // the original/defeatured association.
  const labelSize = Math.max(gap * 0.055, 1.5);

  return (
    <>
      <ambientLight intensity={0.85} />
      <directionalLight position={[1, 2, 3]} intensity={1.2} />
      <directionalLight position={[-2, -1, -1]} intensity={0.5} />
      <Suspense fallback={<Html center>Lade Original…</Html>}>
        <Model modelId={originalId} position={[0, 0, 0]} highlightIds={originalHi} />
      </Suspense>
      <Suspense fallback={null}>
        <Model modelId={defeaturedId} position={[gap, 0, 0]} highlightIds={defeaturedHi} />
      </Suspense>
      <Grid
        position={[gap / 2, -0.01, 0]}
        args={[gap * 4, gap * 4]}
        cellColor="#c7ccd4"
        sectionColor="#a3aab5"
        infiniteGrid
        fadeDistance={gap * 8}
      />
      <Text
        position={[0, 0.02, 0]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={labelSize}
        color="#475569"
        anchorX="center"
        anchorY="middle"
      >
        ORIGINAL
      </Text>
      <Text
        position={[gap, 0.02, 0]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={labelSize}
        color="#475569"
        anchorX="center"
        anchorY="middle"
      >
        DEFEATURED
      </Text>
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
      <Canvas camera={{ position: [gap, gap, gap * 1.6], fov: 45, near: 0.1, far: gap * 40 }}>
        <color attach="background" args={["#e7eaef"]} />
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
