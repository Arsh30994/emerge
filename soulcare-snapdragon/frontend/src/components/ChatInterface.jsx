import { useEffect, useRef, useState } from "react";

/**
 * ChatInterface — text conversation surface for SoulCare.
 */
export default function ChatInterface({ messages, busy, onSend }) {
  const [draft, setDraft] = useState("");
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  function submit(e) {
    e.preventDefault();
    if (!draft.trim() || busy) return;
    onSend(draft);
    setDraft("");
  }

  return (
    <div className="chat">
      <div className="transcript" role="log" aria-live="polite">
        {messages.map((msg, i) => (
          <article key={i} className={`bubble ${msg.role}`}>
            <header>
              <span>{msg.role === "user" ? "You" : "SoulCare"}</span>
              {msg.via === "voice" ? <em>voice</em> : null}
              {msg.risk?.label ? <em className={`risk-${msg.risk.label}`}>{msg.risk.label}</em> : null}
            </header>
            <p>{msg.text}</p>
            {msg.helpline ? (
              <p className="helpline-note">
                Helpline: {msg.helpline.us}. {msg.helpline.disclaimer}
              </p>
            ) : null}
          </article>
        ))}
        {busy ? <p className="thinking">Listening on-device…</p> : null}
        <div ref={endRef} />
      </div>

      <form className="composer" onSubmit={submit}>
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
        />
        <button type="submit" disabled={busy || !draft.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}
