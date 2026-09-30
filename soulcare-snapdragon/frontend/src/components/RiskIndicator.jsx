/**
 * RiskIndicator — color-coded low / medium / high / critical.
 */
export default function RiskIndicator({ risk, tone, vad }) {
  const level = risk?.risk_level || risk?.label || "—";
  const score = risk ? Math.round((risk.risk_score ?? risk.confidence ?? 0) * 100) : null;

  return (
    <div className={`panel risk-panel level-${risk?.risk_level || risk?.label || "none"}`}>
      <h2>Risk pulse</h2>
      <p className="risk-label">{level}</p>
      {score !== null ? (
        <p className="risk-conf">
          score {score}/100 · {risk.model || risk.backend || "on-device"}
        </p>
      ) : (
        <p className="risk-conf">Share a message to classify distress locally (Distil-BERT).</p>
      )}

      {risk?.probabilities ? (
        <ul className="prob-bars">
          {Object.entries(risk.probabilities).map(([k, v]) => (
            <li key={k}>
              <span>{k}</span>
              <div className="bar">
                <i style={{ width: `${Math.round(v * 100)}%` }} />
              </div>
            </li>
          ))}
        </ul>
      ) : null}

      {tone ? (
        <div className="tone-block">
          <h3>Voice tone</h3>
          <p>
            <strong>{tone.tone}</strong>
            {tone.demo ? " (demo)" : " · librosa"}
          </p>
        </div>
      ) : null}

      {vad ? (
        <div className="tone-block">
          <h3>VAD</h3>
          <p>
            {vad.has_speech ? "Speech detected" : "No speech"} · ratio{" "}
            {Math.round((vad.speech_ratio || 0) * 100)}%
          </p>
        </div>
      ) : null}

      {risk?.needs_helpline ? (
        <p className="crisis-banner">
          Elevated distress detected. Please contact 988 (US) or local emergency services.
          SoulCare is not a crisis hotline.
        </p>
      ) : null}
    </div>
  );
}
