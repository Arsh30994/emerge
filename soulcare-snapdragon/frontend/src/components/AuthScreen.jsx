import { useState } from "react";
import { api } from "../api.js";

/**
 * Local login / register / guest — accounts stay on-device.
 */
export default function AuthScreen({ onAuth }) {
  const [mode, setMode] = useState("login");
  const [username, setUsername] = useState("demo");
  const [password, setPassword] = useState("demo123");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const path = mode === "register" ? "/auth/register" : "/auth/login";
      const data = await api(path, {
        method: "POST",
        json: {
          username,
          password,
          display_name: displayName || undefined,
        },
      });
      localStorage.setItem("soulcare_token", data.token);
      localStorage.setItem("soulcare_user", JSON.stringify(data.user));
      onAuth(data.user);
    } catch (err) {
      setError(err.message || "Auth failed");
    } finally {
      setBusy(false);
    }
  }

  async function guest() {
    setBusy(true);
    setError("");
    try {
      const data = await api("/auth/guest", { method: "POST" });
      localStorage.setItem("soulcare_token", data.token);
      localStorage.setItem("soulcare_user", JSON.stringify(data.user));
      onAuth(data.user);
    } catch (err) {
      setError(err.message || "Guest failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-screen">
      <div className="auth-orb" aria-hidden />
      <div className="auth-card animate-in">
        <p className="brand">SoulCare</p>
        <p className="auth-sub">On-device mental health companion for Snapdragon</p>

        <div className="auth-tabs">
          <button
            type="button"
            className={mode === "login" ? "active" : ""}
            onClick={() => setMode("login")}
          >
            Log in
          </button>
          <button
            type="button"
            className={mode === "register" ? "active" : ""}
            onClick={() => setMode("register")}
          >
            Register
          </button>
        </div>

        <form onSubmit={submit} className="auth-form">
          <label>
            Username
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
            />
          </label>
          {mode === "register" ? (
            <label>
              Display name
              <input
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="Optional"
              />
            </label>
          ) : null}
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={mode === "register" ? "new-password" : "current-password"}
              required
            />
          </label>
          {error ? <p className="error">{error}</p> : null}
          <button type="submit" className="primary" disabled={busy}>
            {busy ? "Please wait…" : mode === "register" ? "Create local account" : "Enter SoulCare"}
          </button>
        </form>

        <button type="button" className="ghost" onClick={guest} disabled={busy}>
          Continue as guest
        </button>

        <p className="auth-hint">
          Demo: <code>demo / demo123</code> · Judge: <code>judge / snapdragon</code>
          <br />
          Accounts are stored only on this device.
        </p>
      </div>
    </div>
  );
}
