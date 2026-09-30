import { useCallback, useEffect, useState } from "react";
import ChatInterface from "./components/ChatInterface.jsx";
import RiskIndicator from "./components/RiskIndicator.jsx";
import VoiceInput from "./components/VoiceInput.jsx";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

export default function App() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      text: "Hi — I'm SoulCare. I run entirely on your device. Nothing you share leaves this PC. How are you feeling?",
      risk: null,
    },
  ]);
  const [risk, setRisk] = useState(null);
  const [tone, setTone] = useState(null);
  const [busy, setBusy] = useState(false);
  const [system, setSystem] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch(`${API_BASE}/system`)
      .then((r) => r.json())
      .then(setSystem)
      .catch(() =>
        setError("Backend offline. Start it with: cd soulcare-snapdragon/backend && python main.py")
      );
  }, []);

  const sendText = useCallback(async (text) => {
    const trimmed = text.trim();
    if (!trimmed || busy) return;
    setBusy(true);
    setError("");
    setMessages((m) => [...m, { role: "user", text: trimmed }]);
    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: trimmed, tone }),
      });
      if (!res.ok) throw new Error(`Chat failed (${res.status})`);
      const data = await res.json();
      setRisk(data.risk);
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          text: data.response.reply,
          risk: data.risk,
          helpline: data.response.helpline,
          metrics: data.metrics,
        },
      ]);
    } catch (err) {
      setError(err.message || "Request failed");
    } finally {
      setBusy(false);
    }
  }, [busy, tone]);

  const sendVoice = useCallback(async (blob) => {
    if (!blob || busy) return;
    setBusy(true);
    setError("");
    try {
      const form = new FormData();
      form.append("file", blob, "voice.webm");
      form.append("include_tone", "true");
      const res = await fetch(`${API_BASE}/voice-chat`, {
        method: "POST",
        body: form,
      });
      if (!res.ok) throw new Error(`Voice chat failed (${res.status})`);
      const data = await res.json();
      setRisk(data.risk);
      setTone(data.tone);
      setMessages((m) => [
        ...m,
        {
          role: "user",
          text: data.transcript?.text || "(voice)",
          via: "voice",
          tone: data.tone,
        },
        {
          role: "assistant",
          text: data.response.reply,
          risk: data.risk,
          helpline: data.response.helpline,
        },
      ]);
    } catch (err) {
      setError(err.message || "Voice request failed");
    } finally {
      setBusy(false);
    }
  }, [busy]);

  const accel = system?.snapdragon?.preferred_accelerator || "…";

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand-block">
          <p className="brand">SoulCare</p>
          <p className="tagline">On-device mental health companion</p>
        </div>
        <div className="status-pills">
          <span className="pill">Offline-capable</span>
          <span className="pill">Privacy-first</span>
          <span className="pill accent">Snapdragon · {accel}</span>
        </div>
      </header>

      <main className="layout">
        <section className="stage">
          <ChatInterface messages={messages} busy={busy} onSend={sendText} />
          <VoiceInput busy={busy} onAudio={sendVoice} />
          {error ? <p className="error">{error}</p> : null}
        </section>

        <aside className="side">
          <RiskIndicator risk={risk} tone={tone} />
          <div className="panel">
            <h2>On this device</h2>
            <ul className="facts">
              <li>Speech → Whisper (local)</li>
              <li>Risk → TF-IDF + LogReg</li>
              <li>Tone → librosa features</li>
              <li>Reply → rules / Phi-3 local</li>
            </ul>
            <p className="fineprint">
              Mental health data never leaves this laptop. No OpenAI, Gemini, or cloud APIs.
            </p>
            {system?.components ? (
              <dl className="meta">
                <div><dt>STT</dt><dd>{system.components.stt}</dd></div>
                <div><dt>Tone</dt><dd>{system.components.tone}</dd></div>
                <div><dt>LLM</dt><dd>{system.components.response}</dd></div>
              </dl>
            ) : null}
          </div>
        </aside>
      </main>
    </div>
  );
}
