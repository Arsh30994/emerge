/**
 * Settings drawer — theme, agentic mode, export, clear.
 */
export default function SettingsPanel({
  open,
  onClose,
  theme,
  onTheme,
  agentic,
  onAgentic,
  onExport,
  onClear,
  onBreathing,
}) {
  if (!open) return null;
  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <aside className="settings-drawer animate-in" onClick={(e) => e.stopPropagation()}>
        <header>
          <h2>Settings</h2>
          <button type="button" className="ghost" onClick={onClose}>
            Close
          </button>
        </header>

        <label className="switch-row">
          <span>Theme</span>
          <select value={theme} onChange={(e) => onTheme(e.target.value)}>
            <option value="dark">Dark</option>
            <option value="light">Light</option>
          </select>
        </label>

        <label className="switch-row">
          <span>Agentic AI</span>
          <input
            type="checkbox"
            checked={agentic}
            onChange={(e) => onAgentic(e.target.checked)}
          />
        </label>

        <div className="settings-actions">
          <button type="button" onClick={onBreathing}>
            Start breathing exercise
          </button>
          <button type="button" onClick={onExport}>
            Export conversation
          </button>
          <button type="button" className="danger" onClick={onClear}>
            Clear chat
          </button>
        </div>

        <p className="fineprint">
          SoulCare keeps sessions on this device. Clearing chat does not delete your local account.
        </p>
      </aside>
    </div>
  );
}
