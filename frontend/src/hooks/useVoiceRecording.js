import { useCallback, useRef, useState } from "react";
import { transcribeAudio } from "../api/ai";

// Sostituisce window.SpeechRecognition (Web Speech API nativa del browser),
// che Safari/WebKit non implementa affatto — quindi assente su OGNI browser
// su iPhone, non solo "serve Chrome". Registra l'audio grezzo con
// MediaRecorder (già usata nel progetto per comprimere i video caricati nei
// documenti, funziona su iOS da 14.3+) e lo fa trascrivere lato server
// (Whisper, vedi backend/services/transcription_service.py) — stessa
// esperienza su tutti i browser, non solo su quelli con supporto nativo.
// Condiviso da AIAssistant.jsx e VoiceAssistant.jsx (prima duplicavano la
// stessa logica SpeechRecognition ciascuno per conto proprio).
//
// Differenza di comportamento rispetto a prima: SpeechRecognition si
// fermava da sola al termine dell'enunciato (pausa nel parlato). MediaRecorder
// non ha un rilevamento di silenzio integrato: qui la registrazione si ferma
// solo quando l'utente tocca di nuovo il pulsante (tocca per iniziare, tocca
// per finire — come un messaggio vocale) o al tetto massimo di MAX_RECORDING_MS,
// quello che arriva prima.
const MAX_RECORDING_MS = 60_000;
const PREFERRED_MIME_TYPES = ["audio/webm", "audio/mp4", "audio/ogg"];

function pickMimeType() {
  if (typeof MediaRecorder === "undefined" || !MediaRecorder.isTypeSupported) return undefined;
  return PREFERRED_MIME_TYPES.find((t) => MediaRecorder.isTypeSupported(t));
}

function microphoneErrorMessage(err) {
  if (err?.name === "NotAllowedError" || err?.name === "SecurityError") {
    return "Permesso del microfono negato. Controlla le impostazioni del browser.";
  }
  if (err?.name === "NotFoundError") return "Nessun microfono disponibile.";
  return "Non sono riuscito ad accedere al microfono. Riprova.";
}

/**
 * @param {{ onTranscribed: (text: string) => void, onError: (message: string) => void }} handlers
 * @returns {{ status: "idle"|"recording"|"transcribing", toggle: () => void, stop: () => void }}
 */
export default function useVoiceRecording({ onTranscribed, onError }) {
  const [status, setStatus] = useState("idle");
  const recorderRef = useRef(null);
  const streamRef = useRef(null);
  const chunksRef = useRef([]);
  const maxDurationTimerRef = useRef(null);

  const releaseStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  }, []);

  const stop = useCallback(() => {
    if (maxDurationTimerRef.current) {
      clearTimeout(maxDurationTimerRef.current);
      maxDurationTimerRef.current = null;
    }
    if (recorderRef.current && recorderRef.current.state !== "inactive") {
      recorderRef.current.stop();
    }
  }, []);

  const start = useCallback(async () => {
    if (typeof MediaRecorder === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      onError?.("Il tuo browser non supporta la registrazione audio.");
      return;
    }
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
      onError?.(microphoneErrorMessage(err));
      return;
    }
    streamRef.current = stream;
    chunksRef.current = [];
    const mimeType = pickMimeType();
    const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };
    recorder.onstop = async () => {
      releaseStream();
      const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
      chunksRef.current = [];
      if (blob.size === 0) {
        setStatus("idle");
        return;
      }
      setStatus("transcribing");
      try {
        const data = await transcribeAudio(blob);
        setStatus("idle");
        onTranscribed?.(data.text);
      } catch (err) {
        setStatus("idle");
        const detail = err?.response?.data?.detail;
        onError?.(typeof detail === "string" ? detail : "Non sono riuscito a trascrivere l'audio. Riprova.");
      }
    };

    recorderRef.current = recorder;
    recorder.start();
    setStatus("recording");
    maxDurationTimerRef.current = setTimeout(stop, MAX_RECORDING_MS);
  }, [onError, onTranscribed, releaseStream, stop]);

  const toggle = useCallback(() => {
    if (status === "recording") stop();
    else if (status === "idle") start();
  }, [status, start, stop]);

  return { status, toggle, stop };
}
