import { useCallback, useEffect, useMemo, useState } from "react";
import { api, API_BASE } from "./api";
import AgentSteps from "./components/AgentSteps";
import AuthScreen from "./components/AuthScreen";
import BreathingModal from "./components/BreathingModal";
import ChatInterface from "./components/ChatInterface";
import OfflineBadge from "./components/OfflineBadge";
import RiskIndicator from "./components/RiskIndicator";
import SettingsPanel from "./components/SettingsPanel";
import VoiceInput from "./components/VoiceInput";
import type {
  AgentInfo,
  AuthUser,
  ChatResponse,
  Message,
  RiskResult,
  SystemStatus,
  ToneResult,
  VadResult,
} from "./types";

const WELCOME =
  "Hi — I'm SoulCare, your on-device agentic companion. I use Qualcomm AI Hub models on this PC. Nothing leaves the device. How are you feeling?";

function loadUser(): AuthUser | null {
  try {
    return JSON.parse(localStorage.getItem("soulcare_user") || "null") as AuthUser | null;
  } catch {
    return null;
  }
}

interface ChatApiResult {
  risk: RiskResult;
  response: ChatResponse;
  agent?: AgentInfo | null;
  tone?: ToneResult | null;
  vad?: VadResult | null;
  transcript?: { text?: string };
}

export default function App() {
  const [user, setUser] = useState<AuthUser | null>(loadUser);
  const [theme, setTheme] = useState<"dark" | "light">(
    () => (localStorage.getItem("soulcare_theme") as "dark" | "light") || "dark"
  );
  const [agentic, setAgentic] = useState(() => localStorage.getItem("soulcare_agentic") !== "0");
  const [messages, setMessages] = useState<Message[]>([
    { role: "assistant", text: WELCOME, risk: null },
  ]);
  const [draft, setDraft] = useState("");
  const [risk, setRisk] = useState<RiskResult | null>(null);
  const [tone, setTone] = useState<ToneResult | null>(null);
  const [vad, setVad] = useState<VadResult | null>(null);
  const [agentInfo, setAgentInfo] = useState<AgentInfo | null>(null);
  const [busy, setBusy] = useState(false);
  const [system, setSystem] = useState<SystemStatus | null>(null);
  const [error, setError] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [breatheOpen, setBreatheOpen] = useState(false);
  const [mood, setMood] = useState<string | null>(null);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("soulcare_theme", theme);
  }, [theme]);

  useEffect(() => {
    localStorage.setItem("soulcare_agentic", agentic ? "1" : "0");
  }, [agentic]);

  useEffect(() => {
    api<SystemStatus>("/health")
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
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || busy) return;
      setBusy(true);
      setError("");
      setMessages((m) => [...m, { role: "user", text: trimmed }]);
      try {
        const data = await api<ChatApiResult>("/chat", {
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
        setError(err instanceof Error ? err.message : "Request failed");
      } finally {
        setBusy(false);
      }
    },
    [busy, tone, history, agentic]
  );

  const sendVoice = useCallback(
    async (blob: Blob) => {
      if (!blob || busy) return;
      setBusy(true);
      setError("");
      try {
        const form = new FormData();
        form.append("file", blob, "voice.webm");
        form.append("include_tone", "true");
        form.append("agentic", agentic ? "true" : "false");
        const token = localStorage.getItem("soulcare_token");
        const res = await fetch(`${API_BASE}/voice-chat`, {
          method: "POST",
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          body: form,
        });
        if (!res.ok) throw new Error(`Voice chat failed (${res.status})`);
        const data = (await res.json()) as ChatApiResult;
        setRisk(data.risk);
        setTone(data.tone || null);
        setVad(data.vad || null);
        setAgentInfo(data.agent || null);
        setMessages((m) => [
          ...m,
          {
            role: "user",
            text: data.transcript?.text || "(voice)",
            via: "voice",
            tone: data.tone || undefined,
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
        setError(err instanceof Error ? err.message : "Voice request failed");
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

  function pickMood(value: string) {
    setMood(value);
    void sendText(`My mood check-in: I feel ${value}.`);
  }

  if (!user) {
    return <AuthScreen onAuth={setUser} />;
  }

  return (
    <div className="relative flex min-h-screen flex-col overflow-x-hidden">
      <div
        className="pointer-events-none fixed inset-0 -z-10 bg-[radial-gradient(900px_480px_at_8%_-8%,rgba(111,191,154,0.2),transparent_55%),radial-gradient(700px_420px_at_100%_0%,rgba(196,163,90,0.16),transparent_50%),linear-gradient(165deg,var(--bg0),var(--bg1))]"
        aria-hidden
      />

      <header className="animate-rise flex flex-wrap items-end justify-between gap-3 border-b border-[var(--line)] px-6 py-4 backdrop-blur md:px-8">
        <div>
          <p className="font-display m-0 text-4xl md:text-5xl">SoulCare</p>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Hello, {user.display_name || user.username}
            {agentic ? " · Agentic mode" : ""}
          </p>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2">
          <OfflineBadge system={system} />
          <button
            type="button"
            className="rounded-full border border-[var(--line)] bg-[var(--card)] px-3 py-2 text-sm"
            onClick={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
          >
            {theme === "dark" ? "Light" : "Dark"}
          </button>
          <button
            type="button"
            className="rounded-full border border-[var(--line)] bg-[var(--card)] px-3 py-2 text-sm"
            onClick={() => setSettingsOpen(true)}
          >
            Settings
          </button>
          <button
            type="button"
            className="rounded-full border border-crisis/40 px-3 py-2 text-sm text-crisis"
            onClick={() => void logout()}
          >
            Log out
          </button>
        </div>
      </header>

      <div className="animate-rise flex flex-wrap items-center gap-2 px-6 pt-3 text-sm text-[var(--muted)] md:px-8">
        <span>Mood check-in</span>
        {["calm", "okay", "low", "anxious", "overwhelmed"].map((m) => (
          <button
            key={m}
            type="button"
            disabled={busy}
            onClick={() => pickMood(m)}
            className={`rounded-full border px-3 py-1 capitalize ${
              mood === m
                ? "border-gold-400/50 bg-gold-400/15 text-gold-400"
                : "border-[var(--line)] bg-[var(--card)]"
            }`}
          >
            {m}
          </button>
        ))}
      </div>

      <main className="grid flex-1 gap-4 px-6 py-4 md:grid-cols-[1.55fr_0.9fr] md:px-8">
        <section className="flex min-h-0 flex-col gap-3">
          <ChatInterface
            messages={messages}
            busy={busy}
            onSend={(t) => void sendText(t)}
            draft={draft}
            setDraft={setDraft}
          />
          <VoiceInput
            busy={busy}
            onAudio={(b) => void sendVoice(b)}
            onTranscript={setDraft}
            vadPreview={vad}
          />
          {error ? <p className="m-0 text-sm text-crisis">{error}</p> : null}
        </section>

        <aside className="flex flex-col gap-4">
          <RiskIndicator risk={risk} tone={tone} vad={vad} />
          <AgentSteps agent={agentInfo} />
          <div className="animate-rise rounded-2xl border border-[var(--line)] bg-[var(--card)] p-4 shadow-lg backdrop-blur">
            <h2 className="font-display mb-2 text-xl">On this device</h2>
            <ul className="m-0 list-disc pl-5 text-sm leading-7 text-[var(--muted)]">
              <li>Whisper-Small · Silero-VAD (AI Hub App)</li>
              <li>Distil-BERT risk · Phi-3.5 reply</li>
              <li>Agent tools: breathe, ground, helpline</li>
              <li>Targets: STT &lt;100ms · risk &lt;50ms · E2E &lt;2s</li>
            </ul>
            <div className="mt-3 flex flex-wrap gap-2">
              <button type="button" className="rounded-full border border-[var(--line)] px-3 py-1.5 text-sm" onClick={() => setBreatheOpen(true)}>
                Breathe
              </button>
              <button type="button" className="rounded-full border border-[var(--line)] px-3 py-1.5 text-sm" onClick={exportChat}>
                Export
              </button>
              <button type="button" className="rounded-full border border-[var(--line)] px-3 py-1.5 text-sm" onClick={() => setAgentic((v) => !v)}>
                Agent {agentic ? "ON" : "OFF"}
              </button>
            </div>
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
