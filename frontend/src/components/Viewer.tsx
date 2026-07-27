import { Suspense, useEffect, useMemo, useRef } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, useGLTF, Grid, Html, Text, GizmoHelper, GizmoViewport } from "@react-three/drei";
import * as THREE from "three";
import { geometryUrl } from "../api";
import { useT } from "../i18n";
import type { FeatureChange } from "../types";
import { backgroundOf, partColorOf, useViewerTheme } from "../viewerTheme";
import { ViewerControls } from "./ViewerControls";

const HIGHLIGHT_COLOR = new THREE.Color("#f59e0b");
// Dihedral angle (degrees) above which an edge is drawn -- keeps rounded
// fillets smooth while still outlining every real feature boundary.
const EDGE_THRESHOLD_DEG = 20;
const BLACK = new THREE.Color("#000000");

/**
 * One model, with the faces belonging to the selected feature painted in the
 * highlight colour. Each mesh gets its own material so colouring one face never
 * bleeds into another (and never mutates the cached glTF).
 */
function Model({
  modelId,
  position,
  highlightIds,
  baseColor,
  edgeColor,
}: {
  modelId: string;
  position: [number, number, number];
  highlightIds: Set<string>;
  baseColor: string;
  edgeColor: string;
}) {
  const { scene } = useGLTF(geometryUrl(modelId));

  const cloned = useMemo(() => {
    const copy = scene.clone(true);
    copy.traverse((obj) => {
      const mesh = obj as THREE.Mesh;
      if (mesh.isMesh) {
        mesh.material = new THREE.MeshStandardMaterial({
          metalness: 0.1,
          roughness: 0.7,
          side: THREE.DoubleSide,
        });
        // Crisp CAD-style edge lines on top of the shaded face, so feature
        // boundaries (fillet start, hole rim, ...) stay legible without
        // relying on lighting gradients alone.
        const edges = new THREE.LineSegments(
          new THREE.EdgesGeometry(mesh.geometry, EDGE_THRESHOLD_DEG),
          new THREE.LineBasicMaterial(),
        );
        edges.name = "__edges";
        mesh.add(edges);
      }
    });
    return copy;
  }, [scene]);

  useEffect(() => {
    const base = new THREE.Color(baseColor);
    cloned.traverse((obj) => {
      const mesh = obj as THREE.Mesh;
      if (!mesh.isMesh) return;
      const mat = mesh.material as THREE.MeshStandardMaterial;
      const on = highlightIds.has(mesh.name);
      mat.color.copy(on ? HIGHLIGHT_COLOR : base);
      mat.emissive.copy(on ? HIGHLIGHT_COLOR : BLACK);
      mat.emissiveIntensity = on ? 0.4 : 0;
    });
  }, [cloned, highlightIds, baseColor]);

  // Edge lines follow the background, not the part: they have to stay readable
  // on white as well as on dark grey.
  useEffect(() => {
    const colour = new THREE.Color(edgeColor);
    cloned.traverse((obj) => {
      if (obj.name !== "__edges") return;
      ((obj as THREE.LineSegments).material as THREE.LineBasicMaterial).color.copy(colour);
    });
  }, [cloned, edgeColor]);

  return <primitive object={cloned} position={position} />;
}

/**
 * Floor "imprint" label that always faces the camera.
 *
 * It rides on a circle around its model and turns with the orbit, so it stays
 * between the viewer and the part: upright from every angle, and never drawn
 * across the geometry it is labelling.
 */
function FloorLabel({
  center,
  radius,
  fontSize,
  color,
  children,
}: {
  center: [number, number, number];
  radius: number;
  fontSize: number;
  color: string;
  children: string;
}) {
  const group = useRef<THREE.Group>(null);

  useFrame(({ camera }) => {
    const node = group.current;
    if (!node) return;
    const dx = camera.position.x - center[0];
    const dz = camera.position.z - center[2];
    const len = Math.hypot(dx, dz) || 1;
    node.position.set(center[0] + (dx / len) * radius, center[1], center[2] + (dz / len) * radius);
    // Lay the text flat (child) and spin the group so its baseline runs across
    // the viewing direction -- see the child's -90° rotation about X.
    node.rotation.set(0, Math.atan2(dx, dz), 0);
  });

  return (
    <group ref={group}>
      <Text
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={fontSize}
        color={color}
        letterSpacing={0.18}
        anchorX="center"
        anchorY="middle"
      >
        {children}
      </Text>
    </group>
  );
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

/** Frames both models in the viewport, keeping the current viewing direction. */
function fitToModels(
  camera: THREE.PerspectiveCamera,
  controls: any,
  models: THREE.Object3D | null,
) {
  if (!controls || !models) return;
  const box = new THREE.Box3().setFromObject(models);
  if (box.isEmpty()) return;

  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  const half = Math.max(size.x, size.y, size.z) / 2;
  const vFov = (camera.fov * Math.PI) / 180;
  // Distance that fits the bounding sphere vertically, then horizontally --
  // whichever is larger wins, so nothing is cropped on a wide or tall canvas.
  const distance =
    1.25 * Math.max(half / Math.tan(vFov / 2), half / Math.tan(vFov / 2) / camera.aspect);

  const direction = camera.position.clone().sub(controls.target);
  if (direction.lengthSq() < 1e-6) direction.set(1, 0.9, 1.6);
  direction.normalize().multiplyScalar(distance);

  controls.target.copy(center);
  camera.position.copy(center).add(direction);
  camera.near = Math.max(distance / 1000, 0.01);
  camera.far = distance * 100;
  camera.updateProjectionMatrix();
  controls.update();
}

function Scene({
  originalId,
  defeaturedId,
  feature,
  gap,
  fitRef,
}: {
  originalId: string;
  defeaturedId: string;
  feature: FeatureChange | null;
  gap: number;
  fitRef: React.MutableRefObject<() => void>;
}) {
  const controls = useRef<any>(null);
  const models = useRef<THREE.Group>(null);
  const { camera } = useThree();
  const { t } = useT();
  const theme = backgroundOf(useViewerTheme((s) => s.background));
  const partColor = partColorOf(useViewerTheme((s) => s.partColor));

  useEffect(() => {
    camera.position.set(gap * 1.1, gap * 0.9, gap * 1.6);
  }, [camera, gap]);

  // Hand the toolbar (rendered outside the canvas) a way to reset the view.
  useEffect(() => {
    fitRef.current = () =>
      fitToModels(camera as THREE.PerspectiveCamera, controls.current, models.current);
  }, [camera, fitRef]);

  const originalHi = useMemo(
    () => new Set(feature?.geometry_refs.original_face_ids ?? []),
    [feature],
  );
  const defeaturedHi = useMemo(
    () => new Set(feature?.geometry_refs.defeatured_face_ids ?? []),
    [feature],
  );

  const labelSize = Math.max(gap * 0.055, 1.5);
  const labelRadius = gap * 0.45;

  return (
    <>
      <ambientLight intensity={0.85} />
      <directionalLight position={[1, 2, 3]} intensity={1.2} />
      <directionalLight position={[-2, -1, -1]} intensity={0.5} />
      <group ref={models}>
        <Suspense fallback={<Html center>{t("viewer.loading")}</Html>}>
          <Model
            modelId={originalId}
            position={[0, 0, 0]}
            highlightIds={originalHi}
            baseColor={partColor}
            edgeColor={theme.edge}
          />
        </Suspense>
        <Suspense fallback={null}>
          <Model
            modelId={defeaturedId}
            position={[gap, 0, 0]}
            highlightIds={defeaturedHi}
            baseColor={partColor}
            edgeColor={theme.edge}
          />
        </Suspense>
      </group>
      <Grid
        position={[gap / 2, -0.01, 0]}
        args={[gap * 4, gap * 4]}
        cellColor={theme.gridCell}
        sectionColor={theme.gridSection}
        infiniteGrid
        fadeDistance={gap * 8}
      />
      <FloorLabel
        center={[0, 0.02, 0]}
        radius={labelRadius}
        fontSize={labelSize}
        color={theme.label}
      >
        {t("viewer.original")}
      </FloorLabel>
      <FloorLabel
        center={[gap, 0.02, 0]}
        radius={labelRadius}
        fontSize={labelSize}
        color={theme.label}
      >
        {t("viewer.defeatured")}
      </FloorLabel>
      <OrbitControls ref={controls} makeDefault target={[gap / 2, 0, 0]} />
      <FocusTarget controls={controls} feature={feature} />
      <GizmoHelper alignment="bottom-right" margin={[64, 64]} onUpdate={() => controls.current?.update()}>
        <GizmoViewport axisColors={["#f87171", "#4ade80", "#60a5fa"]} labelColor="black" />
      </GizmoHelper>
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
  const theme = backgroundOf(useViewerTheme((s) => s.background));
  const fitRef = useRef<() => void>(() => {});

  return (
    <div className="relative h-full w-full">
      <Canvas camera={{ position: [gap, gap, gap * 1.6], fov: 45, near: 0.1, far: gap * 40 }}>
        <color attach="background" args={[theme.bg]} />
        <Scene
          originalId={originalId}
          defeaturedId={defeaturedId}
          feature={feature}
          gap={gap}
          fitRef={fitRef}
        />
      </Canvas>
      <ViewerControls onFit={() => fitRef.current()} />
    </div>
  );
}
