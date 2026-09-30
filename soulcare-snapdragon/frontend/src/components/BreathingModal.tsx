import { useEffect, useState } from "react";

interface Props {
  open: boolean;
  onClose: () => void;
}

const PHASES = [
  { label: "Inhale", seconds: 4 },
  { label: "Hold", seconds: 7 },
  { label: "Exhale", seconds: 8 },
] as const;

export default function BreathingModal({ open, onClose }: Props) {
  const [phaseIdx, setPhaseIdx] = useState(0);
  const [left, setLeft] = useState<number>(PHASES[0].seconds);
  const [cycle, setCycle] = useState(1);

  useEffect(() => {
    if (!open) return undefined;
    setPhaseIdx(0);
    setLeft(PHASES[0].seconds);
    setCycle(1);
    const id = window.setInterval(() => {
      setLeft((s) => {
        if (s > 1) return s - 1;
        setPhaseIdx((p) => {
          const next = (p + 1) % PHASES.length;
          if (next === 0) setCycle((c) => c + 1);
          setLeft(PHASES[next].seconds);
          return next;
        });
        return 0;
      });
    }, 1000);
    return () => window.clearInterval(id);
  }, [open]);

  if (!open) return null;
  const phase = PHASES[phaseIdx];
  const cls =
    phase.label === "Inhale"
      ? "breath-inhale"
      : phase.label === "Hold"
        ? "breath-hold"
        : "breath-exhale";

  return (
    <div className="fixed inset-0 z-40 grid place-items-center bg-black/45 p-4" onClick={onClose} role="presentation">
      <div
        className="animate-rise w-full max-w-sm rounded-2xl border border-[var(--line)] bg-[var(--card)] p-5 text-center shadow-2xl backdrop-blur"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
      >
        <h2 className="font-display text-2xl">4-7-8 Breath</h2>
        <div
          className={`mx-auto my-4 grid h-40 w-40 place-items-center rounded-full border-2 border-gold-400/45 bg-gold-400/15 transition-transform duration-1000 ${cls}`}
        >
          <span className="text-sm text-[var(--muted)]">{phase.label}</span>
          <strong className="font-display text-4xl">{left}</strong>
        </div>
        <p className="text-sm text-[var(--muted)]">Cycle {Math.min(cycle, 3)} / 3</p>
        <button type="button" className="mt-3 rounded-xl bg-gold-400 px-4 py-2 font-semibold text-[#1a1408]" onClick={onClose}>
          Done
        </button>
      </div>
    </div>
  );
}
