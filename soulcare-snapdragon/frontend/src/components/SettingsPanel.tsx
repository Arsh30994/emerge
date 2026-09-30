interface Props {
  open: boolean;
  onClose: () => void;
  theme: "dark" | "light";
  onTheme: (theme: "dark" | "light") => void;
  agentic: boolean;
  onAgentic: (value: boolean) => void;
  onExport: () => void;
  onClear: () => void;
  onBreathing: () => void;
}

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
}: Props) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-40 bg-black/45 p-4" onClick={onClose} role="presentation">
      <aside
        className="animate-rise ml-auto min-h-[520px] w-full max-w-sm rounded-2xl border border-[var(--line)] bg-[var(--card)] p-5 shadow-2xl backdrop-blur"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="mb-4 flex items-center justify-between">
          <h2 className="font-display m-0 text-2xl">Settings</h2>
          <button type="button" className="rounded-full border border-[var(--line)] px-3 py-1 text-sm" onClick={onClose}>
            Close
          </button>
        </header>

        <label className="flex items-center justify-between gap-4 border-b border-[var(--line)] py-3 text-sm">
          <span>Theme</span>
          <select
            value={theme}
            onChange={(e) => onTheme(e.target.value as "dark" | "light")}
            className="rounded-lg border border-[var(--line)] bg-white/5 px-2 py-1"
          >
            <option value="dark">Dark</option>
            <option value="light">Light</option>
          </select>
        </label>

        <label className="flex items-center justify-between gap-4 border-b border-[var(--line)] py-3 text-sm">
          <span>Agentic AI</span>
          <input type="checkbox" checked={agentic} onChange={(e) => onAgentic(e.target.checked)} />
        </label>

        <div className="mt-4 grid gap-2">
          <button type="button" className="rounded-full border border-[var(--line)] px-3 py-2 text-sm" onClick={onBreathing}>
            Start breathing exercise
          </button>
          <button type="button" className="rounded-full border border-[var(--line)] px-3 py-2 text-sm" onClick={onExport}>
            Export conversation
          </button>
          <button
            type="button"
            className="rounded-full border border-crisis/40 px-3 py-2 text-sm text-crisis"
            onClick={onClear}
          >
            Clear chat
          </button>
        </div>
        <p className="mt-4 text-xs text-[var(--muted)]">
          SoulCare keeps sessions on this device. Clearing chat does not delete your local account.
        </p>
      </aside>
    </div>
  );
}
