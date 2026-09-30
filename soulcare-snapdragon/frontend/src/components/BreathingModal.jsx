import { useEffect, useState } from "react";

/**
 * Guided 4-7-8 breathing overlay.
 */
export default function BreathingModal({ open, onClose }) {
  const phases = [
    { label: "Inhale", seconds: 4 },
    { label: "Hold", seconds: 7 },
    { label: "Exhale", seconds: 8 },
  ];
  const [phaseIdx, setPhaseIdx] = useState(0);
  const [left, setLeft] = useState(phases[0].seconds);
  const [cycle, setCycle] = useState(1);

  useEffect(() => {
    if (!open) return undefined;
    setPhaseIdx(0);
    setLeft(phases[0].seconds);
    setCycle(1);
    const id = setInterval(() => {
      setLeft((s) => {
        if (s > 1) return s - 1;
        setPhaseIdx((p) => {
          const next = (p + 1) % phases.length;
          if (next === 0) setCycle((c) => c + 1);
          setLeft(phases[next].seconds);
          return next;
        });
        return 0;
      });
    }, 1000);
    return () => clearInterval(id);
  }, [open]);

  if (!open) return null;
  const phase = phases[phaseIdx];

  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <div className="modal breathe-modal animate-in" onClick={(e) => e.stopPropagation()} role="dialog">
        <h2>4-7-8 Breath</h2>
        <div className={`breath-circle ${phase.label.toLowerCase()}`}>
          <span>{phase.label}</span>
          <strong>{left}</strong>
        </div>
        <p className="risk-conf">Cycle {Math.min(cycle, 3)} / 3</p>
        <button type="button" className="primary" onClick={onClose}>
          Done
        </button>
      </div>
    </div>
  );
}
