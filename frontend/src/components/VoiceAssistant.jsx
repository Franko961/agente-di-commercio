import { useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { Mic, MicOff, Loader2, X, Volume2, VolumeX, Sparkles } from "lucide-react";
import api from "../api";
import { cleanForSpeech } from "../utils/speechClean";
import AIActionConfirm from "./AIActionConfirm";

/**
 * Pulsante microfono globale, sempre visibile in tutte le pagine dell'app (montato in Layout.jsx).
 * Permette di parlare con l'assistente AI da qualsiasi schermata senza aprire la pagina Assistente AI,
 * riusando lo stesso endpoint /api/ai/chat (quindi le stesse capacità: aggiungere clienti, offerte, ecc.).
 */
export default function VoiceAssistant() {
  const location = useLocation();
  const [status, setStatus] = useState("idle"); // idle | listening | sending | result | error
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [speaking, setSpeaking] = useState(false);
  const [pendingActions, setPendingActions] = useState([]);
  const [executingIdx, setExecutingIdx] = useState(null);
  const recognitionRef = useRef(null);
  const synthRef = useRef(window.speechSynthesis);

  // Non mostrare il pulsante nella pagina Assistente AI (già dedicata alla chat completa)
  const hideOnThisPage = location.pathname.startsWith("/app/ai");

  const speak = (text) => {
    if (!synthRef.current || !text) return;
    synthRef.current.cancel();
    const clean = cleanForSpeech(text);
    if (!clean) return;
    const utterance = new SpeechSynthesisUtterance(clean);
    utterance.lang = "it-IT";
    utterance.rate = 1.05;
    const voices = synthRef.current.getVoices();
    const itVoice = voices.find((v) => v.lang.startsWith("it")) || voices[0];
    if (itVoice) utterance.voice = itVoice;
    utterance.onstart = () => setSpeaking(true);
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    synthRef.current.speak(utterance);
  };

  const stopSpeaking = () => {
    synthRef.current?.cancel();
    setSpeaking(false);
  };

  const sendToAI = async (text) => {
    setQuestion(text);
    setStatus("sending");
    try {
      const { data } = await api.post("/ai/chat", { message: text, channel: "voice" });
      const actions = data.actions || [];
      const fullText = actions.length > 0 ? actions.join("\n") + (data.response ? "\n\n" + data.response : "") : data.response;
      setAnswer(fullText || "Fatto.");
      setPendingActions(data.pending_actions || []);
      setStatus("result");
      speak(data.response);
    } catch (e) {
      setErrorMsg("Errore di comunicazione con l'AI. Riprova tra poco.");
      setStatus("error");
    }
  };

  const confirmAction = async (idx, resolvedInput) => {
    const action = pendingActions[idx];
    setExecutingIdx(idx);
    try {
      const { data } = await api.post("/ai/execute-action", {
        tool_name: action.tool_name, resolved_input: resolvedInput, log_id: action.log_id,
      });
      setAnswer((prev) => `${prev}\n\n${data.message}`);
      setPendingActions((prev) => prev.filter((_, i) => i !== idx));
      speak(data.message);
    } catch (e) {
      setAnswer((prev) => `${prev}\n\n❌ Errore durante la registrazione. Riprova.`);
    } finally {
      setExecutingIdx(null);
    }
  };

  const cancelAction = async (idx) => {
    const action = pendingActions[idx];
    setPendingActions((prev) => prev.filter((_, i) => i !== idx));
    try {
      await api.post("/ai/cancel-action", { log_id: action.log_id });
    } catch (e) {
      // L'azione è comunque rimossa dallo schermo anche se il log non si aggiorna.
    }
  };

  const startListening = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setErrorMsg("Il tuo browser non supporta il riconoscimento vocale. Usa Chrome o Edge.");
      setStatus("error");
      return;
    }
    stopSpeaking();
    setQuestion("");
    setAnswer("");
    setErrorMsg("");
    setPendingActions([]);
    const rec = new SpeechRecognition();
    rec.lang = "it-IT";
    rec.continuous = false;
    rec.interimResults = false;
    rec.onresult = (e) => {
      const transcript = e.results[0][0].transcript;
      sendToAI(transcript);
    };
    rec.onerror = () => {
      setErrorMsg("Non ho sentito bene. Riprova.");
      setStatus("error");
    };
    rec.onend = () => {
      setStatus((s) => (s === "listening" ? "idle" : s));
    };
    recognitionRef.current = rec;
    setStatus("listening");
    rec.start();
  };

  const handleMicClick = () => {
    if (status === "listening") {
      recognitionRef.current?.stop();
      setStatus("idle");
      return;
    }
    startListening();
  };

  const close = () => {
    stopSpeaking();
    recognitionRef.current?.stop();
    setStatus("idle");
    setQuestion("");
    setAnswer("");
    setErrorMsg("");
    setPendingActions([]);
  };

  const isOpen = status !== "idle";

  if (hideOnThisPage) return null;

  return (
    <div className="fixed z-40 bottom-20 md:bottom-6 right-4 md:right-6 flex flex-col items-end">
      {/* Pannello risultato / stato */}
      {isOpen && (
        <div
          data-testid="voice-assistant-panel"
          className="mb-3 w-[340px] max-w-[88vw] bg-white border border-[#E4E4E1] rounded-md shadow-xl p-4 fade-up"
        >
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-widest text-[#FF5A00]">
              <Sparkles className="w-3.5 h-3.5" /> Salesfly
            </div>
            <button onClick={close} className="p-1 text-[#A1A1AA] hover:text-[#0A0A0A] rounded" title="Chiudi">
              <X className="w-4 h-4" />
            </button>
          </div>

          {status === "listening" && (
            <div className="flex items-center gap-2 text-[13px] text-[#52525B] py-3">
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500" />
              </span>
              Ti ascolto…
            </div>
          )}

          {status === "sending" && (
            <div className="space-y-2">
              {question && <div className="text-[13px] text-[#52525B] italic">"{question}"</div>}
              <div className="flex items-center gap-2 text-[13px] text-[#52525B]">
                <Loader2 className="w-3.5 h-3.5 animate-spin" /> Sto pensando…
              </div>
            </div>
          )}

          {status === "result" && (
            <div className="space-y-2">
              {question && <div className="text-[12px] text-[#A1A1AA] italic">"{question}"</div>}
              <div className="text-[13px] text-[#0A0A0A] whitespace-pre-line">{answer}</div>
              {pendingActions.map((action, idx) => (
                <AIActionConfirm
                  key={idx}
                  action={action}
                  busy={executingIdx === idx}
                  onConfirm={(resolved) => confirmAction(idx, resolved)}
                  onCancel={() => cancelAction(idx)}
                />
              ))}
              <div className="flex items-center justify-between pt-2">
                <button
                  onClick={speaking ? stopSpeaking : () => speak(answer)}
                  className="flex items-center gap-1.5 text-[11px] font-mono uppercase tracking-widest text-[#52525B] hover:text-[#0A192F]"
                >
                  {speaking ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
                  {speaking ? "Interrompi" : "Riascolta"}
                </button>
                <button
                  onClick={startListening}
                  className="flex items-center gap-1.5 text-[11px] font-mono uppercase tracking-widest text-[#FF5A00]"
                >
                  <Mic className="w-3.5 h-3.5" /> Nuova domanda
                </button>
              </div>
            </div>
          )}

          {status === "error" && (
            <div className="space-y-2">
              <div className="text-[13px] text-red-600">{errorMsg}</div>
              <button
                onClick={startListening}
                className="flex items-center gap-1.5 text-[11px] font-mono uppercase tracking-widest text-[#FF5A00]"
              >
                <Mic className="w-3.5 h-3.5" /> Riprova
              </button>
            </div>
          )}
        </div>
      )}

      {/* Pulsante microfono */}
      <button
        data-testid="voice-assistant-button"
        onClick={handleMicClick}
        aria-label="Parla con Salesfly"
        title="Parla con Salesfly"
        className={`flex items-center gap-2 rounded-full shadow-lg pl-4 pr-4 md:pr-5 py-3.5 md:py-3 transition-all duration-200 ${
          status === "listening" ? "bg-red-500 hover:bg-red-600" : "bg-[#0A192F] hover:bg-[#172A45]"
        } text-white`}
      >
        {status === "sending" ? (
          <Loader2 className="w-5 h-5 animate-spin shrink-0" />
        ) : status === "listening" ? (
          <MicOff className="w-5 h-5 shrink-0" />
        ) : (
          <Mic className="w-5 h-5 shrink-0" />
        )}
        <span className="hidden md:inline text-[13px] font-medium whitespace-nowrap">Parla con Salesfly</span>
      </button>
    </div>
  );
}
