import { useEffect, useRef, useState } from "react";
import { useT } from "../i18n";
import { BACKGROUNDS, PART_COLORS, useViewerTheme } from "../viewerTheme";

/**
 * Floating viewer toolbar, stacked above the orientation gizmo in the corner.
 *
 * The colour menus fly out sideways rather than upwards: the toolbar sits at
 * the bottom edge, so there is room to the left but not above.
 */
export function ViewerControls({ onFit }: { onFit: () => void }) {
  const { t } = useT();
  const partColor = useViewerTheme((s) => s.partColor);
  const background = useViewerTheme((s) => s.background);
  const setPartColor = useViewerTheme((s) => s.setPartColor);
  const setBackground = useViewerTheme((s) => s.setBackground);
  const [open, setOpen] = useState<"part" | "background" | null>(null);
  const root = useRef<HTMLDivElement>(null);

  // Clicking anywhere else -- including into the 3D canvas -- closes the flyout.
  useEffect(() => {
    if (!open) return;
    function onPointerDown(e: PointerEvent) {
      if (!root.current?.contains(e.target as Node)) setOpen(null);
    }
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [open]);

  const toggle = (which: "part" | "background") =>
    setOpen((current) => (current === which ? null : which));

  return (
    <div
      ref={root}
      className="pointer-events-auto absolute flex flex-col gap-1.5"
      // Aligned with the gizmo's centre (64 px from the corner) and clear of it.
      style={{ right: 44, bottom: 148 }}
    >
      <ToolButton
        label={t("viewer.background")}
        icon={<BackgroundIcon />}
        onClick={() => toggle("background")}
        flyout={
          open === "background" && (
            <Swatches
              items={BACKGROUNDS.map((b) => ({
                key: b.key,
                hex: b.swatch,
                label: t(`viewer.bg.${b.key}`),
              }))}
              active={background}
              onPick={(key) => {
                setBackground(key);
                setOpen(null);
              }}
            />
          )
        }
      />

      <ToolButton
        label={t("viewer.partColor")}
        icon={<PaletteIcon />}
        onClick={() => toggle("part")}
        flyout={
          open === "part" && (
            <Swatches
              items={PART_COLORS.map((c) => ({
                key: c.key,
                hex: c.hex,
                label: t(`viewer.color.${c.key}`),
              }))}
              active={partColor}
              onPick={(key) => {
                setPartColor(key);
                setOpen(null);
              }}
            />
          )
        }
      />

      <ToolButton
        label={t("viewer.center")}
        icon={<FitIcon />}
        onClick={() => {
          setOpen(null);
          onFit();
        }}
      />
    </div>
  );
}

function ToolButton({
  label,
  icon,
  onClick,
  flyout,
}: {
  label: string;
  icon: React.ReactNode;
  onClick: () => void;
  flyout?: React.ReactNode;
}) {
  return (
    <div className="relative">
      {flyout}
      <button
        onClick={onClick}
        title={label}
        aria-label={label}
        className="flex h-10 w-10 items-center justify-center rounded-lg border border-black/10 bg-white/85 text-slate-600 shadow-sm backdrop-blur transition hover:bg-white hover:text-slate-900"
      >
        {icon}
      </button>
    </div>
  );
}

function Swatches({
  items,
  active,
  onPick,
}: {
  items: { key: string; hex: string; label: string }[];
  active: string;
  onPick: (key: string) => void;
}) {
  return (
    <div className="absolute right-full top-0 mr-2 flex h-10 items-center gap-1.5 rounded-lg border border-black/10 bg-white/90 px-2 shadow-md backdrop-blur">
      {items.map((item) => (
        <button
          key={item.key}
          onClick={() => onPick(item.key)}
          title={item.label}
          aria-label={item.label}
          aria-pressed={item.key === active}
          style={{ background: item.hex }}
          className={`h-6 w-6 rounded-full border transition ${
            item.key === active
              ? "border-amber-500 ring-2 ring-amber-400/60"
              : "border-black/20 hover:scale-110"
          }`}
        />
      ))}
    </div>
  );
}

/* Icons: 20px, 1.6 stroke, matching the toolbar's light chrome. */

function FitIcon() {
  return (
    <Icon>
      <path d="M3 7V4h3M17 7V4h-3M3 13v3h3M17 13v3h-3" />
      <circle cx="10" cy="10" r="2.6" />
    </Icon>
  );
}

function PaletteIcon() {
  return (
    <Icon>
      <path d="M10 3a7 7 0 1 0 0 14c1 0 1.4-.7 1-1.4-.5-.9.1-1.9 1.2-1.9H14a3 3 0 0 0 3-3A7 7 0 0 0 10 3Z" />
      <circle cx="7" cy="8" r=".9" fill="currentColor" stroke="none" />
      <circle cx="10.5" cy="6.4" r=".9" fill="currentColor" stroke="none" />
      <circle cx="13.6" cy="8.6" r=".9" fill="currentColor" stroke="none" />
    </Icon>
  );
}

function BackgroundIcon() {
  return (
    <Icon>
      <rect x="3" y="3" width="14" height="14" rx="2.5" />
      <path d="M3 12.5 7 9l3.5 3M12 11.5 14 10l3 2.5" />
    </Icon>
  );
}

function Icon({ children }: { children: React.ReactNode }) {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {children}
    </svg>
  );
}
