import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, useGLTF, Grid, Html, Text, GizmoHelper, GizmoViewport } from "@react-three/drei";
import * as THREE from "three";
import { geometryUrl } from "../api";
import { useT } from "../i18n";
import type { FeatureChange } from "../types";
import {
  clipPlanes,
  floorLevels,
  footprintCorners,
  labelPlacement,
  modelBounds,
  quadrantOf,
} from "../viewerLayout";
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
  onBounds,
}: {
  modelId: string;
  position: [number, number, number];
  highlightIds: Set<string>;
  baseColor: string;
  edgeColor: string;
  onBounds?: (box: THREE.Box3) => void;
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

  // World-space bounding box of this model, so the floor label can trace the
  // real footprint instead of a guessed radius. Depends on the position
  // components, not on the array: a fresh `[0, 0, 0]` literal on every render
  // would re-run the effect and loop against the parent's state update.
  const [px, py, pz] = position;
  useEffect(() => {
    if (!onBounds) return;
    const box = modelBounds(cloned);
    if (!box.isEmpty()) onBounds(box);
  }, [cloned, onBounds, px, py, pz]);

  return <primitive object={cloned} position={position} />;
}

/**
 * Floor annotation for one model: the outline of its footprint plus the name
 * written along one edge of that rectangle, like a plan-view drawing.
 *
 * The outline is world-fixed and turns with the scene. The caption jumps
 * between the four edges as the camera orbits, always landing on the edge
 * nearest the viewer -- that keeps it upright and outside the part from every
 * direction, without the wobble of a continuously camera-facing label.
 */
function FootprintLabel({
  box,
  floorY,
  color,
  minFontSize,
  children,
}: {
  box: THREE.Box3;
  floorY: number;
  color: string;
  minFontSize: number;
  children: string;
}) {
  const group = useRef<THREE.Group>(null);

  const { center, size, outline } = useMemo(() => {
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    // Padded, so the outline never coincides with a vertical wall of a part
    // standing exactly on its bounding box.
    const geometry = new THREE.BufferGeometry().setFromPoints(
      footprintCorners(box.min, box.max).map((c) => new THREE.Vector3(c.x, floorY, c.z)),
    );
    const outline = new THREE.LineLoop(geometry, new THREE.LineBasicMaterial({ color }));
    return { center, size, outline };
  }, [box, floorY, color]);

  useEffect(() => () => {
    outline.geometry.dispose();
    (outline.material as THREE.Material).dispose();
  }, [outline]);

  const [quadrant, setQuadrant] = useState(0);
  useFrame(({ camera }) => {
    const next = quadrantOf(camera.position, center);
    if (next !== quadrant) setQuadrant(next);
  });

  const { yaw, dir, offset, fontSize } = labelPlacement(quadrant, size, minFontSize);

  return (
    <>
      {/* Already built in world coordinates -- kept outside the rotating group. */}
      <primitive object={outline} />
      <group
        ref={group}
        position={[center.x + dir.x * offset, floorY, center.z + dir.z * offset]}
        rotation={[0, yaw, 0]}
      >
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
    </>
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
  setClipPlanes(camera, distance);
  controls.update();
}

/** Applies `clipPlanes` to a camera; see viewerLayout for the reasoning. */
function setClipPlanes(camera: THREE.PerspectiveCamera, distance: number) {
  const { near, far } = clipPlanes(distance);
  camera.near = near;
  camera.far = far;
  camera.updateProjectionMatrix();
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
  const [originalBox, setOriginalBox] = useState<THREE.Box3 | null>(null);
  const [defeaturedBox, setDefeaturedBox] = useState<THREE.Box3 | null>(null);

  useEffect(() => {
    camera.position.set(gap * 1.1, gap * 0.9, gap * 1.6);
    setClipPlanes(camera as THREE.PerspectiveCamera, gap * 2);
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

  const loaded = [originalBox, defeaturedBox].filter(Boolean) as THREE.Box3[];
  const lowest = loaded.length ? Math.min(...loaded.map((b) => b.min.y)) : null;
  const { floorY, labelY } = floorLevels(lowest, gap);
  const minLabelSize = Math.max(gap * 0.04, 1.5);

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
            onBounds={setOriginalBox}
          />
        </Suspense>
        <Suspense fallback={null}>
          <Model
            modelId={defeaturedId}
            position={[gap, 0, 0]}
            highlightIds={defeaturedHi}
            baseColor={partColor}
            edgeColor={theme.edge}
            onBounds={setDefeaturedBox}
          />
        </Suspense>
      </group>
      <Grid
        position={[gap / 2, floorY, 0]}
        args={[gap * 4, gap * 4]}
        cellColor={theme.gridCell}
        sectionColor={theme.gridSection}
        infiniteGrid
        fadeDistance={gap * 8}
      />
      {originalBox && (
        <FootprintLabel
          box={originalBox}
          floorY={labelY}
          color={theme.label}
          minFontSize={minLabelSize}
        >
          {t("viewer.original")}
        </FootprintLabel>
      )}
      {defeaturedBox && (
        <FootprintLabel
          box={defeaturedBox}
          floorY={labelY}
          color={theme.label}
          minFontSize={minLabelSize}
        >
          {t("viewer.defeatured")}
        </FootprintLabel>
      )}
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
      <Canvas
        camera={{ position: [gap, gap, gap * 1.6], fov: 45, near: gap / 25, far: gap * 20 }}
      >
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
