import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./api.js";
import AgentSteps from "./components/AgentSteps.jsx";
import AuthScreen from "./components/AuthScreen.jsx";
import BreathingModal from "./components/BreathingModal.jsx";
import ChatInterface from "./components/ChatInterface.jsx";
import OfflineBadge from "./components/OfflineBadge.jsx";
import RiskIndicator from "./components/RiskIndicator.jsx";
import SettingsPanel from "./components/SettingsPanel.jsx";
import VoiceInput from "./components/VoiceInput.jsx";

const WELCOME =
  "Hi — I'm SoulCare, your on-device agentic companion. I use Qualcomm AI Hub models on this PC. Nothing leaves the device. How are you feeling?";

function loadUser() {
  try {
    return JSON.parse(localStorage.getItem("soulcare_user") || "null");
  } catch {
    return null;
  }
}

export default function App() {
  const [user, setUser] = useState(loadUser);
  const [theme, setTheme] = useState(() => localStorage.getItem("soulcare_theme") || "dark");
  const [agentic, setAgentic] = useState(() => localStorage.getItem("soulcare_agentic") !== "0");
  const [messages, setMessages] = useState([{ role: "assistant", text: WELCOME, risk: null }]);
  const [risk, setRisk] = useState(null);
  const [tone, setTone] = useState(null);
  const [vad, setVad] = useState(null);
  const [agentInfo, setAgentInfo] = useState(null);
  const [busy, setBusy] = useState(false);
  const [system, setSystem] = useState(null);
  const [error, setError] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [breatheOpen, setBreatheOpen] = useState(false);
  const [mood, setMood] = useState(null);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("soulcare_theme", theme);
  }, [theme]);

  useEffect(() => {
    localStorage.setItem("soulcare_agentic", agentic ? "1" : "0");
  }, [agentic]);

  useEffect(() => {
    api("/health")
      .then(setSystem)
      .catch(() => setError("Backend offline. Run: cd soulcare-snapdragon/backend && python main.py"));
  }, []);

  const history = useMemo(
    () => messages.slice(-8).map((m) => ({ role: m.role, text: m.text })),
    [messages]
  );

  const logout = useCallback(async () => {
    try {
      await api("/auth/logout", { method: "POST" });
    } catch {
      /* ignore */
    }
    localStorage.removeItem("soulcare_token");
    localStorage.removeItem("soulcare_user");
    setUser(null);
    setMessages([{ role: "assistant", text: WELCOME, risk: null }]);
    setRisk(null);
    setAgentInfo(null);
  }, []);

  const sendText = useCallback(
    async (text) => {
      const trimmed = text.trim();
      if (!trimmed || busy) return;
      setBusy(true);
      setError("");
      setMessages((m) => [...m, { role: "user", text: trimmed }]);
      try {
        const data = await api("/chat", {
          method: "POST",
          json: { text: trimmed, tone, history, agentic },
        });
        setRisk(data.risk);
        setAgentInfo(data.agent || null);
        setMessages((m) => [
          ...m,
          {
            role: "assistant",
            text: data.response.reply,
            risk: data.risk,
            helpline: data.response.helpline,
            agent: data.agent,
            model: data.response.model,
          },
        ]);
      } catch (err) {
        setError(err.message || "Request failed");
      } finally {
        setBusy(false);
      }
    },
    [busy, tone, history, agentic]
  );

  const sendVoice = useCallback(
    async (blob) => {
      if (!blob || busy) return;
      setBusy(true);
      setError("");
      try {
        const form = new FormData();
        form.append("file", blob, "voice.webm");
        form.append("include_tone", "true");
        form.append("agentic", agentic ? "true" : "false");
        const token = localStorage.getItem("soulcare_token");
        const res = await fetch(
          `${import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000"}/voice-chat`,
          {
            method: "POST",
            headers: token ? { Authorization: `Bearer ${token}` } : {},
            body: form,
          }
        );
        if (!res.ok) throw new Error(`Voice chat failed (${res.status})`);
        const data = await res.json();
        setRisk(data.risk);
        setTone(data.tone);
        setVad(data.vad);
        setAgentInfo(data.agent || null);
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
            agent: data.agent,
            model: data.response.model,
          },
        ]);
      } catch (err) {
        setError(err.message || "Voice request failed");
      } finally {
        setBusy(false);
      }
    },
    [busy, agentic]
  );

  function exportChat() {
    const payload = {
      exported_at: new Date().toISOString(),
      user,
      messages,
      risk,
      agent: agentInfo,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `soulcare-session-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function clearChat() {
    setMessages([{ role: "assistant", text: WELCOME, risk: null }]);
    setRisk(null);
    setTone(null);
    setVad(null);
    setAgentInfo(null);
    setSettingsOpen(false);
  }

  function pickMood(value) {
    setMood(value);
    sendText(`My mood check-in: I feel ${value}.`);
  }

  if (!user) {
    return <AuthScreen onAuth={setUser} />;
  }

  return (
    <div className="shell">
      <div className="ambient" aria-hidden />
      <header className="topbar animate-in">
        <div className="brand-block">
          <p className="brand">SoulCare</p>
          <p className="tagline">
            Hello, {user.display_name || user.username}
            {agentic ? " · Agentic mode" : ""}
          </p>
        </div>
        <div className="top-actions">
          <OfflineBadge system={system} />
          <button
            type="button"
            className="icon-btn"
            onClick={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
            title="Toggle theme"
          >
            {theme === "dark" ? "Light" : "Dark"}
          </button>
          <button type="button" className="icon-btn" onClick={() => setSettingsOpen(true)}>
            Settings
          </button>
          <button type="button" className="icon-btn danger-text" onClick={logout}>
            Log out
          </button>
        </div>
      </header>

      <div className="mood-row animate-in">
        <span>Mood check-in</span>
        {["calm", "okay", "low", "anxious", "overwhelmed"].map((m) => (
          <button
            key={m}
            type="button"
            className={`mood-chip ${mood === m ? "active" : ""}`}
            onClick={() => pickMood(m)}
            disabled={busy}
          >
            {m}
          </button>
        ))}
      </div>

      <main className="layout">
        <section className="stage">
          <ChatInterface messages={messages} busy={busy} onSend={sendText} />
          <VoiceInput busy={busy} onAudio={sendVoice} vadPreview={vad} />
          {error ? <p className="error">{error}</p> : null}
        </section>

        <aside className="side">
          <RiskIndicator risk={risk} tone={tone} vad={vad} />
          <AgentSteps agent={agentInfo} />
          <div className="panel animate-in">
            <h2>On this device</h2>
            <ul className="facts">
              <li>Whisper-Small · Silero-VAD</li>
              <li>Distil-BERT risk · Phi-3.5 reply</li>
              <li>Agent tools: breathe, ground, helpline</li>
            </ul>
            <div className="quick-actions">
              <button type="button" onClick={() => setBreatheOpen(true)}>
                Breathe
              </button>
              <button type="button" onClick={exportChat}>
                Export
              </button>
              <button type="button" onClick={() => setAgentic((v) => !v)}>
                Agent {agentic ? "ON" : "OFF"}
              </button>
            </div>
            {system?.models ? (
              <dl className="meta">
                <div>
                  <dt>STT</dt>
                  <dd>{system.models.stt}</dd>
                </div>
                <div>
                  <dt>Agent</dt>
                  <dd>{system.models.agent}</dd>
                </div>
                <div>
                  <dt>Risk</dt>
                  <dd>{system.models.risk}</dd>
                </div>
              </dl>
            ) : null}
          </div>
        </aside>
      </main>

      <SettingsPanel
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        theme={theme}
        onTheme={setTheme}
        agentic={agentic}
        onAgentic={setAgentic}
        onExport={exportChat}
        onClear={clearChat}
        onBreathing={() => {
          setSettingsOpen(false);
          setBreatheOpen(true);
        }}
      />
      <BreathingModal open={breatheOpen} onClose={() => setBreatheOpen(false)} />
    </div>
  );
}
