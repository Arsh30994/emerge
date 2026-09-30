import { useRef, useState } from "react";
import type { VadResult } from "../types";
import { API_BASE } from "../api";

interface Props {
  busy: boolean;
  onAudio: (blob: Blob) => void;
  onTranscript?: (text: string) => void;
  vadPreview: VadResult | null;
}

/** Capture mic → WAV/webm → optional /transcribe preview → parent voice-chat. */
export default function VoiceInput({ busy, onAudio, onTranscript, vadPreview }: Props) {
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [levels, setLevels] = useState<number[]>(() => Array(24).fill(0.08));
  const mediaRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | null>(null);
  const rafRef = useRef<number | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);

  async function start() {
    if (busy || recording) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        stream.getTracks().forEach((t) => t.stop());
        if (audioCtxRef.current) {
          void audioCtxRef.current.close();
          audioCtxRef.current = null;
        }
        if (rafRef.current) cancelAnimationFrame(rafRef.current);

        // Optional: fill composer with local Whisper transcription
        if (onTranscript) {
          try {
            const form = new FormData();
            form.append("file", blob, "voice.webm");
            const token = localStorage.getItem("soulcare_token");
            const res = await fetch(`${API_BASE}/transcribe`, {
              method: "POST",
              headers: token ? { Authorization: `Bearer ${token}` } : {},
              body: form,
            });
            if (res.ok) {
              const data = (await res.json()) as { text?: string };
              if (data.text) onTranscript(data.text);
            }
          } catch {
            /* voice-chat still proceeds */
          }
        }
        onAudio(blob);
      };
      mediaRef.current = recorder;
      recorder.start();
      setRecording(true);
      setSeconds(0);
      timerRef.current = window.setInterval(() => setSeconds((s) => s + 1), 1000);

      const ctx = new AudioContext();
      audioCtxRef.current = ctx;
      const source = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      const data = new Uint8Array(analyser.frequencyBinCount);
      const tick = () => {
        analyser.getByteTimeDomainData(data);
        let sum = 0;
        for (let i = 0; i < data.length; i++) {
          const v = (data[i] - 128) / 128;
          sum += v * v;
        }
        const rms = Math.sqrt(sum / data.length);
        setLevels((prev) => [...prev.slice(1), Math.min(1, rms * 4)]);
        rafRef.current = requestAnimationFrame(tick);
      };
      tick();
    } catch {
      alert("Microphone access is required for voice input.");
    }
  }

  function stop() {
    if (!recording) return;
    if (timerRef.current) window.clearInterval(timerRef.current);
    mediaRef.current?.stop();
    setRecording(false);
  }

  const bars = vadPreview?.waveform_preview?.length
    ? vadPreview.waveform_preview
    : levels;

  return (
    <div className={`flex flex-wrap items-center gap-3 ${recording ? "opacity-100" : ""}`}>
      <button
        type="button"
        onClick={recording ? stop : start}
        disabled={busy}
        aria-pressed={recording}
        className={`rounded-xl px-4 py-3 font-semibold disabled:opacity-50 ${
          recording ? "animate-pulse-soft bg-alert text-white" : "bg-gold-400 text-[#1a1408]"
        }`}
      >
        {recording ? "Stop & send" : "Tap to talk"}
      </button>
      <div className="flex h-9 min-w-[120px] items-end gap-0.5" aria-hidden>
        {bars.slice(0, 24).map((v, i) => (
          <i
            key={i}
            className="block w-1 rounded-full bg-gradient-to-t from-safe to-gold-400"
            style={{ height: `${8 + Math.min(1, Number(v)) * 28}px` }}
          />
        ))}
      </div>
      <p className="m-0 text-sm text-[var(--muted)]">
        {recording
          ? `Recording ${seconds}s · Silero-VAD → Whisper-Small`
          : "Voice stays on this PC — Whisper-Small via Qualcomm AI Hub"}
      </p>
    </div>
  );
}
