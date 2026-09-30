import { useState, type FormEvent } from "react";
import { api } from "../api";
import type { AuthUser } from "../types";

interface Props {
  onAuth: (user: AuthUser) => void;
}

interface AuthPayload {
  token: string;
  user: AuthUser;
}

export default function AuthScreen({ onAuth }: Props) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("demo");
  const [password, setPassword] = useState("demo123");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const path = mode === "register" ? "/auth/register" : "/auth/login";
      const data = await api<AuthPayload>(path, {
        method: "POST",
        json: { username, password, display_name: displayName || undefined },
      });
      localStorage.setItem("soulcare_token", data.token);
      localStorage.setItem("soulcare_user", JSON.stringify(data.user));
      onAuth(data.user);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Auth failed");
    } finally {
      setBusy(false);
    }
  }

  async function guest() {
    setBusy(true);
    setError("");
    try {
      const data = await api<AuthPayload>("/auth/guest", { method: "POST" });
      localStorage.setItem("soulcare_token", data.token);
      localStorage.setItem("soulcare_user", JSON.stringify(data.user));
      onAuth(data.user);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Guest failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className="relative grid min-h-screen place-items-center overflow-hidden p-6"
      style={{
        background:
          "radial-gradient(800px 400px at 20% 10%, rgba(111,191,154,0.2), transparent 60%), linear-gradient(160deg, var(--bg0), var(--bg1) 55%, var(--bg2))",
      }}
    >
      <div
        className="pointer-events-none absolute h-[420px] w-[420px] rounded-full bg-[radial-gradient(circle,rgba(196,163,90,0.28),transparent_65%)] blur-md"
        style={{ animation: "floatOrb 8s ease-in-out infinite" }}
        aria-hidden
      />
      <div className="animate-rise relative z-10 w-full max-w-md rounded-3xl border border-[var(--line)] bg-[var(--card)] p-6 shadow-2xl backdrop-blur">
        <p className="font-display m-0 text-4xl">SoulCare</p>
        <p className="mt-1 text-[var(--muted)]">On-device mental health companion for Snapdragon</p>

        <div className="mt-4 grid grid-cols-2 gap-2">
          {(["login", "register"] as const).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setMode(m)}
              className={`rounded-full border px-3 py-2 text-sm capitalize ${
                mode === m
                  ? "border-gold-400/50 bg-gold-400/15 text-gold-400"
                  : "border-[var(--line)] bg-transparent"
              }`}
            >
              {m === "login" ? "Log in" : "Register"}
            </button>
          ))}
        </div>

        <form onSubmit={submit} className="mt-4 grid gap-3">
          <label className="grid gap-1 text-sm text-[var(--muted)]">
            Username
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              className="rounded-xl border border-[var(--line)] bg-white/5 px-3 py-2 text-[var(--ink)]"
            />
          </label>
          {mode === "register" ? (
            <label className="grid gap-1 text-sm text-[var(--muted)]">
              Display name
              <input
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                className="rounded-xl border border-[var(--line)] bg-white/5 px-3 py-2 text-[var(--ink)]"
              />
            </label>
          ) : null}
          <label className="grid gap-1 text-sm text-[var(--muted)]">
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="rounded-xl border border-[var(--line)] bg-white/5 px-3 py-2 text-[var(--ink)]"
            />
          </label>
          {error ? <p className="m-0 text-sm text-crisis">{error}</p> : null}
          <button
            type="submit"
            disabled={busy}
            className="rounded-xl bg-gold-400 px-4 py-3 font-semibold text-[#1a1408] disabled:opacity-50"
          >
            {busy ? "Please wait…" : mode === "register" ? "Create local account" : "Enter SoulCare"}
          </button>
        </form>

        <button
          type="button"
          onClick={guest}
          disabled={busy}
          className="mt-2 w-full rounded-full border border-[var(--line)] px-4 py-2 text-sm"
        >
          Continue as guest
        </button>
        <p className="mt-4 text-xs leading-relaxed text-[var(--muted)]">
          Demo: <code className="text-gold-400">demo / demo123</code> · Judge:{" "}
          <code className="text-gold-400">judge / snapdragon</code>
          <br />
          Accounts stay on this device. No cloud auth.
        </p>
      </div>
    </div>
  );
}
