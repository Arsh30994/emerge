import type { RiskResult, ToneResult, VadResult } from "../types";

interface Props {
  risk: RiskResult | null;
  tone: ToneResult | null;
  vad: VadResult | null;
}

const LEVEL_COLOR: Record<string, string> = {
  low: "text-safe",
  medium: "text-warn",
  high: "text-alert",
  critical: "text-crisis",
};

/** Color-coded risk badge: green / yellow / orange / red. */
export default function RiskIndicator({ risk, tone, vad }: Props) {
  const level = risk?.risk_level || risk?.label || "—";
  const score =
    risk != null ? Math.round((risk.risk_score ?? risk.confidence ?? 0) * 100) : null;
  const color = LEVEL_COLOR[String(level)] || "text-[var(--ink)]";

  return (
    <div className="animate-rise rounded-2xl border border-[var(--line)] bg-[var(--card)] p-4 shadow-lg backdrop-blur">
      <h2 className="font-display mb-1 text-xl">Risk pulse</h2>
      <p className={`font-display m-0 text-3xl capitalize ${color}`}>{level}</p>
      <p className="mt-1 text-sm text-[var(--muted)]">
        {score !== null
          ? `score ${score}/100 · ${risk?.model || risk?.backend || "on-device"}`
          : "Share a message to classify distress locally (Distil-BERT)."}
      </p>

      {risk?.probabilities ? (
        <ul className="mt-3 grid gap-2">
          {Object.entries(risk.probabilities).map(([k, v]) => (
            <li key={k} className="grid grid-cols-[72px_1fr] items-center gap-2 text-xs text-[var(--muted)]">
              <span>{k}</span>
              <div className="h-2 overflow-hidden rounded-full bg-black/10">
                <i
                  className="block h-full rounded-full bg-gradient-to-r from-safe to-gold-400"
                  style={{ width: `${Math.round(v * 100)}%` }}
                />
              </div>
            </li>
          ))}
        </ul>
      ) : null}

      {tone ? (
        <div className="mt-4">
          <h3 className="font-display text-lg">Voice tone</h3>
          <p className="text-sm">
            <strong>{tone.tone}</strong>
            {tone.demo ? " (demo)" : " · librosa"}
          </p>
        </div>
      ) : null}

      {vad ? (
        <div className="mt-3">
          <h3 className="font-display text-lg">VAD</h3>
          <p className="text-sm text-[var(--muted)]">
            {vad.has_speech ? "Speech detected" : "No speech"} · ratio{" "}
            {Math.round((vad.speech_ratio || 0) * 100)}%
          </p>
        </div>
      ) : null}

      {risk?.needs_helpline ? (
        <p className="mt-4 rounded-xl border border-crisis/40 bg-crisis/15 p-3 text-sm text-crisis">
          Elevated distress detected. Please contact 988 (US) or local emergency services.
          SoulCare is not a crisis hotline.
        </p>
      ) : null}
    </div>
  );
}
