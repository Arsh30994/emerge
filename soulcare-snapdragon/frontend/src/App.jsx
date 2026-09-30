import { useCallback, useEffect, useState } from "react";
import ChatInterface from "./components/ChatInterface.jsx";
import OfflineBadge from "./components/OfflineBadge.jsx";
import RiskIndicator from "./components/RiskIndicator.jsx";
import VoiceInput from "./components/VoiceInput.jsx";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

export default function App() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      text: "Hi — I'm SoulCare. I run on Qualcomm AI Hub models on your device. Nothing you share leaves this PC. How are you feeling?",
      risk: null,
    },
  ]);
  const [risk, setRisk] = useState(null);
  const [tone, setTone] = useState(null);
  const [vad, setVad] = useState(null);
  const [busy, setBusy] = useState(false);
  const [system, setSystem] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then((r) => r.json())
      .then(setSystem)
      .catch(() =>
        setError("Backend offline. Start: cd soulcare-snapdragon/backend && python main.py")
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
          model: data.response.model,
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
      setVad(data.vad);
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
          model: data.response.model,
        },
      ]);
    } catch (err) {
      setError(err.message || "Voice request failed");
    } finally {
      setBusy(false);
    }
  }, [busy]);

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand-block">
          <p className="brand">SoulCare</p>
          <p className="tagline">On-device mental health · Qualcomm AI Hub</p>
        </div>
        <OfflineBadge system={system} />
      </header>

      <main className="layout">
        <section className="stage">
          <ChatInterface messages={messages} busy={busy} onSend={sendText} />
          <VoiceInput busy={busy} onAudio={sendVoice} vadPreview={vad} />
          {error ? <p className="error">{error}</p> : null}
        </section>

        <aside className="side">
          <RiskIndicator risk={risk} tone={tone} vad={vad} />
          <div className="panel">
            <h2>AI Hub models</h2>
            <ul className="facts">
              <li>STT — Whisper-Small (244MB)</li>
              <li>VAD — Silero (~2MB)</li>
              <li>Risk — Distil-BERT (67MB)</li>
              <li>Reply — Phi-3.5-Mini (2.1GB)</li>
            </ul>
            <p className="fineprint">
              Optimized for Snapdragon X Elite NPU (45 TOPS) via ONNX Runtime + QNN.
              Mental health data never leaves this laptop.
            </p>
            {system?.models ? (
              <dl className="meta">
                <div><dt>STT</dt><dd>{system.models.stt}</dd></div>
                <div><dt>VAD</dt><dd>{system.models.vad}</dd></div>
                <div><dt>Risk</dt><dd>{system.models.risk}</dd></div>
                <div><dt>LLM</dt><dd>{system.models.response}</dd></div>
              </dl>
            ) : null}
          </div>
        </aside>
      </main>
    </div>
  );
}
