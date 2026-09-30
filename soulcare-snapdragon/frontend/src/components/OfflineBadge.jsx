/**
 * OfflineBadge — always-visible "Running Locally" trust signal.
 */
export default function OfflineBadge({ system }) {
  const cloud = system?.cloud_fallback;
  const demo = system?.demo_mode;
  const accel = system?.snapdragon?.preferred_accelerator || "local";

  return (
    <div className={`offline-badge ${cloud ? "mixed" : "local"}`} title="Inference location">
      <span className="dot" aria-hidden />
      <div>
        <strong>{cloud ? "Hybrid demo mode" : "Running Locally"}</strong>
        <small>
          {cloud
            ? "Cloud fallback allowed off-device — disable on Snapdragon"
            : `On-device · ${accel.toUpperCase()} · Qualcomm AI Hub`}
          {demo ? " · demo stubs active" : ""}
        </small>
      </div>
    </div>
  );
}
