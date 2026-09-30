import { useRef, useState } from "react";

/**
 * VoiceInput — records microphone audio and hands a Blob to the parent.
 * Transcription happens locally via Whisper on the FastAPI backend.
 */
export default function VoiceInput({ busy, onAudio }) {
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const mediaRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);

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
        onAudio(blob);
      };
      mediaRef.current = recorder;
      recorder.start();
      setRecording(true);
      setSeconds(0);
      timerRef.current = setInterval(() => setSeconds((s) => s + 1), 1000);
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

  return (
    <div className={`voice ${recording ? "hot" : ""}`}>
      <button
        type="button"
        className="mic"
        onClick={recording ? stop : start}
        disabled={busy}
        aria-pressed={recording}
      >
        {recording ? "Stop & send" : "Hold space — tap to talk"}
      </button>
      <p className="voice-hint">
        {recording
          ? `Recording ${seconds}s · local Whisper will transcribe`
          : "Voice stays on this PC — no cloud STT"}
      </p>
    </div>
  );
}
