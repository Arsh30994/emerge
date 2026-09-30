import { useEffect, useRef, type FormEvent } from "react";
import type { Message } from "../types";

interface Props {
  messages: Message[];
  busy: boolean;
  onSend: (text: string) => void;
  draft: string;
  setDraft: (value: string) => void;
}

export default function ChatInterface({
  messages,
  busy,
  onSend,
  draft,
  setDraft,
}: Props) {
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!draft.trim() || busy) return;
    onSend(draft);
    setDraft("");
  }

  return (
    <div className="flex min-h-[420px] flex-1 flex-col overflow-hidden rounded-2xl border border-[var(--line)] bg-[var(--card)] shadow-xl backdrop-blur">
      <div className="flex flex-1 flex-col gap-3 overflow-y-auto p-4" role="log" aria-live="polite">
        {messages.map((msg, i) => (
          <article
            key={`${msg.role}-${i}`}
            className={`animate-rise max-w-[92%] rounded-2xl border px-4 py-3 ${
              msg.role === "user"
                ? "ml-auto border-gold-400/30 bg-gold-400/15"
                : "mr-auto border-safe/25 bg-safe/10"
            }`}
            style={{ animationDelay: `${Math.min(i, 6) * 40}ms` }}
          >
            <header className="mb-1 flex items-center gap-2 text-[0.72rem] uppercase tracking-wider text-[var(--muted)]">
              <span>{msg.role === "user" ? "You" : "SoulCare"}</span>
              {msg.via === "voice" ? <em className="not-italic">voice</em> : null}
              {msg.agent ? <em className="not-italic">agent</em> : null}
              {msg.risk?.risk_level || msg.risk?.label ? (
                <em className="not-italic">{msg.risk.risk_level || msg.risk.label}</em>
              ) : null}
            </header>
            <p className="m-0 whitespace-pre-wrap leading-relaxed">{msg.text}</p>
            {msg.helpline ? (
              <p className="mt-2 text-sm text-crisis">
                Helpline: {msg.helpline.us}. {msg.helpline.disclaimer}
              </p>
            ) : null}
          </article>
        ))}
        {busy ? <p className="animate-pulse-soft text-sm text-[var(--muted)]">Agent thinking on-device…</p> : null}
        <div ref={endRef} />
      </div>

      <form
        className="flex gap-2 border-t border-[var(--line)] bg-[color-mix(in_srgb,var(--bg0)_70%,transparent)] p-3"
        onSubmit={submit}
      >
        <label className="sr-only" htmlFor="msg">
          Message
        </label>
        <input
          id="msg"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Type how you're feeling…"
          disabled={busy}
          autoComplete="off"
          className="flex-1 rounded-xl border border-[var(--line)] bg-white/5 px-4 py-3 text-[var(--ink)] outline-none focus:outline focus:outline-2 focus:outline-gold-400/50"
        />
        <button
          type="submit"
          disabled={busy || !draft.trim()}
          className="rounded-xl bg-gold-400 px-4 py-3 font-semibold text-[#1a1408] disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  );
}
