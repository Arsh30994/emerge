import { useRef, useState } from "react";

/**
 * VoiceInput — mic capture + live VAD-style level meter.
 */
export default function VoiceInput({ busy, onAudio, vadPreview }) {
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [levels, setLevels] = useState(() => Array(24).fill(0.08));
  const mediaRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);
  const rafRef = useRef(null);
  const audioCtxRef = useRef(null);

  async function start() {
    if (busy || recording) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        stream.getTracks().forEach((t) => t.stop());
        if (audioCtxRef.current) {
          audioCtxRef.current.close().catch(() => {});
          audioCtxRef.current = null;
        }
        cancelAnimationFrame(rafRef.current);
        onAudio(blob);
      };
      mediaRef.current = recorder;
      recorder.start();
      setRecording(true);
      setSeconds(0);
      timerRef.current = setInterval(() => setSeconds((s) => s + 1), 1000);

      // Real-time level visualization (client-side VAD preview)
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
    } catch (err) {
      console.error(err);
      alert("Microphone access is required for voice input.");
    }
  }

  function stop() {
    if (!recording) return;
    clearInterval(timerRef.current);
    mediaRef.current?.stop();
    setRecording(false);
  }

  const bars = vadPreview?.waveform_preview?.length
    ? vadPreview.waveform_preview
    : levels;

  return (
    <div className={`voice ${recording ? "hot" : ""}`}>
      <button
        type="button"
        className="mic"
        onClick={recording ? stop : start}
        disabled={busy}
        aria-pressed={recording}
      >
        {recording ? "Stop & send" : "Tap to talk"}
      </button>
      <div className="vad-meter" aria-hidden>
        {bars.slice(0, 24).map((v, i) => (
          <i key={i} style={{ height: `${8 + Math.min(1, Number(v)) * 28}px` }} />
        ))}
      </div>
      <p className="voice-hint">
        {recording
          ? `Recording ${seconds}s · Silero-VAD gates → Whisper-Small`
          : "Voice stays on this PC — Whisper-Small via Qualcomm AI Hub"}
      </p>
    </div>
  );
}
