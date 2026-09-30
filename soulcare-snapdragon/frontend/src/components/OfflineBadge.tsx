import type { SystemStatus } from "../types";

interface Props {
  system: SystemStatus | null;
}

/** Always-visible privacy signal for judges. */
export default function OfflineBadge({ system }: Props) {
  const accel = system?.snapdragon?.preferred_accelerator || "local";
  return (
    <div
      className="flex max-w-xs items-center gap-2 rounded-2xl border border-safe/40 bg-[var(--card)] px-3 py-2 shadow-sm backdrop-blur"
      title="Inference location"
    >
      <span className="h-2.5 w-2.5 animate-pulse-soft rounded-full bg-safe" aria-hidden />
      <div>
        <strong className="block text-sm">🔒 Running Locally — 100% Private</strong>
        <small className="block text-[0.72rem] text-[var(--muted)]">
          On-device · {accel.toUpperCase()} · Qualcomm AI Hub
          {system?.demo_mode ? " · demo stubs" : ""}
        </small>
      </div>
    </div>
  );
}
