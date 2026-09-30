/**
 * RiskIndicator — visual risk + tone summary for the side panel.
 */
export default function RiskIndicator({ risk, tone }) {
  const label = risk?.label || "—";
  const confidence = risk ? Math.round((risk.confidence || 0) * 100) : null;

  return (
    <div className={`panel risk-panel level-${risk?.label || "none"}`}>
      <h2>Risk pulse</h2>
      <p className="risk-label">{label}</p>
      {confidence !== null ? (
        <p className="risk-conf">{confidence}% confidence · on-device TF-IDF</p>
      ) : (
        <p className="risk-conf">Share a message to classify distress locally.</p>
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
            {tone.demo ? " (demo features)" : " · librosa"}
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
