import { useEffect, useState, useRef, useCallback } from "react";
import api from "../api";
import { Sparkles, Send, Lightbulb, Trash2, Mic, MicOff, Volume2, VolumeX } from "lucide-react";
import { cleanForSpeech } from "../utils/speechClean";
import AIActionConfirm from "../components/AIActionConfirm";

const WELCOME = { role: "assistant", text: "Ciao! Sono il tuo assistente commerciale. Posso suggerirti i clienti più importanti da visitare, analizzare il fatturato e darti consigli pratici. Cosa vuoi sapere?" };

// Messaggi specifici per i codici di errore della Web Speech API
// (SpeechRecognitionErrorEvent.error): prima ogni errore veniva ignorato in
// silenzio (l'ascolto si fermava senza che l'utente capisse perché).
const SPEECH_ERROR_MESSAGES = {
  "not-allowed": "Permesso del microfono negato. Controlla le impostazioni del browser.",
  "audio-capture": "Nessun microfono disponibile.",
  "no-speech": "Non è stata rilevata alcuna voce. Riprova.",
  "network": "Servizio di riconoscimento vocale non raggiungibile.",
  "aborted": "Ascolto interrotto.",
};

export default function AIAssistant() {
  const [messages, setMessages] = useState([WELCOME]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [suggestions, setSuggestions] = useState([]);
  const [listening, setListening] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const [executingKey, setExecutingKey] = useState(null);
  const endRef = useRef(null);
  const recognitionRef = useRef(null);
  const synthRef = useRef(window.speechSynthesis);

  // Inizializza Speech Recognition
  const initRecognition = useCallback(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return null;
    const rec = new SpeechRecognition();
    rec.lang = "it-IT";
    rec.continuous = false;
    rec.interimResults = false;
    rec.onresult = (e) => {
      const transcript = e.results[0][0].transcript;
      setInput(transcript);
      setListening(false);
      // Invia automaticamente dopo la trascrizione
      setTimeout(() => sendVoice(transcript), 100);
    };
    rec.onerror = (event) => {
      setListening(false);
      // A differenza del pannello vocale fluttuante (che è temporaneo), qui
      // i messaggi restano nella cronologia della chat: mostriamo un
      // messaggio solo per errori che richiedono un'azione da parte
      // dell'utente (permesso, microfono, rete). "no-speech" e "aborted"
      // sono frequenti e benigni (silenzio prolungato, stop manuale) e non
      // vanno a intasare la conversazione con un messaggio ogni volta.
      const actionable = ["not-allowed", "audio-capture", "network"];
      if (actionable.includes(event.error)) {
        setMessages(m => [...m, { role: "assistant", text: `⚠️ ${SPEECH_ERROR_MESSAGES[event.error]}` }]);
      }
    };
    rec.onend = () => setListening(false);
    return rec;
  }, []);

  // Text-to-Speech
  const speak = useCallback((text) => {
    if (!voiceEnabled || !synthRef.current) return;
    synthRef.current.cancel();
    // Pulisci il testo da markdown, emoji e simboli prima di leggerlo ad alta voce
    const clean = cleanForSpeech(text);
    const utterance = new SpeechSynthesisUtterance(clean);
    utterance.lang = "it-IT";
    utterance.rate = 1.05;
    utterance.pitch = 1;
    // Cerca voce italiana
    const voices = synthRef.current.getVoices();
    const itVoice = voices.find(v => v.lang.startsWith("it")) || voices[0];
    if (itVoice) utterance.voice = itVoice;
    utterance.onstart = () => setSpeaking(true);
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    synthRef.current.speak(utterance);
  }, [voiceEnabled]);

  const stopSpeaking = () => {
    synthRef.current?.cancel();
    setSpeaking(false);
  };

  const toggleListening = () => {
    if (listening) {
      recognitionRef.current?.stop();
      setListening(false);
      return;
    }
    const rec = initRecognition();
    if (!rec) {
      alert("Il tuo browser non supporta il riconoscimento vocale. Usa Chrome o Edge.");
      return;
    }
    recognitionRef.current = rec;
    rec.start();
    setListening(true);
  };

  const sendVoice = async (text) => {
    if (!text.trim() || busy) return;
    setMessages(m => [...m, { role: "user", text }]);
    setInput("");
    setBusy(true);
    try {
      const { data } = await api.post("/ai/chat", { message: text, channel: "voice" });
      const actions = data.actions || [];
      let fullText = data.response;
      if (actions.length > 0) fullText = actions.join("\n") + (data.response ? "\n\n" + data.response : "");
      setMessages(m => [...m, { role: "assistant", text: fullText, actions, pendingActions: data.pending_actions || [] }]);
      speak(data.response);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      const errMsg = typeof detail === "string" ? detail : "Errore di comunicazione con l'AI.";
      setMessages(m => [...m, { role: "assistant", text: errMsg }]);
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  // Carica cronologia al mount
  useEffect(() => {
    const loadHistory = async () => {
      // Saluto proattivo ("Buongiorno Franco. Hai: ...") al posto del
      // messaggio statico generico: l'assistente non aspetta più solo un
      // comando, apre riassumendo la situazione della giornata. Va
      // recuperato PRIMA della cronologia, perché quest'ultima sostituisce
      // interamente `messages` (vedi sotto).
      let greeting = WELCOME;
      try {
        const { data } = await api.get("/ai/briefing");
        if (data?.text) {
          greeting = { role: "assistant", text: data.text };
        }
      } catch (e) {
        // Se il briefing non è disponibile (errore di rete, ecc.) si
        // ripiega sul saluto statico invece di lasciare la chat vuota.
      }

      try {
        const { data } = await api.get("/ai/history");
        if (data && data.length > 0) {
          const history = data.flatMap(h => [
            { role: "user", text: h.message },
            { role: "assistant", text: h.response },
          ]);
          setMessages([greeting, ...history]);
        } else {
          setMessages([greeting]);
        }
      } catch (e) {
        setMessages([greeting]);
      } finally {
        setLoading(false);
      }

      // Recupera azioni economiche (vendite/offerte, spese sopra soglia)
      // proposte in una sessione precedente e mai confermate né annullate:
      // prima restavano visibili solo nel messaggio di chat originale,
      // quindi ricaricando la pagina la scheda di conferma spariva pur
      // restando "in_attesa" sul DB. Va fatto DOPO aver impostato la
      // cronologia (che sostituisce interamente `messages`), altrimenti
      // questo messaggio verrebbe perso da quella sostituzione.
      try {
        const { data: pending } = await api.get("/ai/pending-actions");
        if (Array.isArray(pending) && pending.length > 0) {
          setMessages(m => [...m, {
            role: "assistant",
            text: "Hai operazioni in sospeso da una richiesta precedente, non ancora confermate:",
            pendingActions: pending,
          }]);
        }
      } catch (e) {
        // nessuna azione pendente o errore di rete: non blocchiamo la chat.
      }
    };
    loadHistory();
    api.get("/ai/suggestions").then(({ data }) => setSuggestions(data.suggestions || [])).catch(() => {});
  }, []);

  const send = async (text) => {
    if (!text.trim() || busy) return;
    setMessages(m => [...m, { role: "user", text }]);
    setInput("");
    setBusy(true);
    try {
      const { data } = await api.post("/ai/chat", { message: text, channel: "chat" });
      const actions = data.actions || [];
      let fullText = data.response;
      if (actions.length > 0) {
        fullText = actions.join("\n") + (data.response ? "\n\n" + data.response : "");
      }
      setMessages(m => [...m, { role: "assistant", text: fullText, actions, pendingActions: data.pending_actions || [] }]);
      speak(data.response);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      const text = typeof detail === "string" ? detail : "Errore di comunicazione con l'AI. Riprova tra poco.";
      setMessages(m => [...m, { role: "assistant", text }]);
    } finally {
      setBusy(false);
    }
  };

  const confirmAction = async (msgIdx, actionIdx, resolvedInput) => {
    const action = messages[msgIdx].pendingActions[actionIdx];
    setExecutingKey(`${msgIdx}-${actionIdx}`);
    try {
      const { data } = await api.post("/ai/execute-action", {
        tool_name: action.tool_name, resolved_input: resolvedInput, log_id: action.log_id,
      });
      setMessages(m => m.map((msg, i) => i === msgIdx
        ? { ...msg, pendingActions: msg.pendingActions.filter((_, j) => j !== actionIdx) }
        : msg
      ).concat([{ role: "assistant", text: data.message }]));
      speak(data.message);
    } catch (err) {
      if (err.response?.status === 409) {
        // L'azione era già stata elaborata: non è un errore da cui
        // l'utente possa "riprovare", va solo rimossa dalla vista perché
        // non è più in sospeso.
        setMessages(m => m.map((msg, i) => i === msgIdx
          ? { ...msg, pendingActions: msg.pendingActions.filter((_, j) => j !== actionIdx) }
          : msg
        ).concat([{ role: "assistant", text: "ℹ️ Questa operazione era già stata elaborata." }]));
      } else {
        setMessages(m => [...m, { role: "assistant", text: "❌ Errore durante la registrazione. Riprova." }]);
      }
    } finally {
      setExecutingKey(null);
    }
  };

  const cancelAction = async (msgIdx, actionIdx) => {
    const action = messages[msgIdx].pendingActions[actionIdx];
    setExecutingKey(`${msgIdx}-${actionIdx}`);
    try {
      await api.post("/ai/cancel-action", { log_id: action.log_id });
      setMessages(m => m.map((msg, i) => i === msgIdx
        ? { ...msg, pendingActions: msg.pendingActions.filter((_, j) => j !== actionIdx) }
        : msg
      ));
    } catch (e) {
      // Non rimuoviamo la scheda se l'annullamento non è confermato dal
      // backend: altrimenti l'azione potrebbe restare "in_attesa" sul DB
      // mentre l'utente crede (a torto) che sia stata annullata.
      setMessages(m => [...m, { role: "assistant", text: "❌ Impossibile annullare l'operazione. Riprova." }]);
    } finally {
      setExecutingKey(null);
    }
  };

  const clearHistory = async () => {
    if (!window.confirm("Cancellare tutta la cronologia della chat?")) return;
    await api.delete("/ai/history");
    setMessages([WELCOME]);
  };

  const quickPrompts = [
    "Quali 3 clienti dovrei visitare questa settimana?",
    "Riassumi le mie vendite del mese",
    "Quali offerte rischiano di scadere?",
    "Analizza la mia pipeline",
  ];

  return (
    <div className="p-4 md:p-8">
      <div className="border-b border-[#E4E4E1] pb-6 mb-6 flex items-end justify-between">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Sparkles className="w-4 h-4 text-[#FF5A00]" />
            <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#FF5A00]">Analisi Previsionale & Suggerimenti</span>
          </div>
          <h1 className="font-cabinet font-black text-3xl md:text-4xl tracking-tight">Assistente AI</h1>
          <p className="text-[14px] text-[#52525B] mt-2">Powered by Claude · Risponde in italiano sui tuoi dati.</p>
        </div>
  <div className="flex items-center gap-2">
          {/* Toggle audio output */}
          <button onClick={() => { setVoiceEnabled(v => !v); stopSpeaking(); }}
            className={`p-2 rounded-md border transition-colors ${voiceEnabled ? "border-[#0A192F] text-[#0A192F]" : "border-[#E4E4E1] text-[#A1A1AA]"}`}
            title={voiceEnabled ? "Disattiva voce AI" : "Attiva voce AI"}>
            {voiceEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
          </button>
          <button onClick={clearHistory} className="flex items-center gap-2 px-3 py-2 border border-[#E4E4E1] hover:border-red-300 hover:text-red-500 rounded-md text-[12px] text-[#A1A1AA] transition-colors">
            <Trash2 className="w-3.5 h-3.5" /> Cancella chat
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-4">
        {/* Chat */}
        <div className="bg-white border border-[#E4E4E1] rounded-md flex flex-col min-h-[60vh]">
          <div className="flex-1 overflow-y-auto p-5 space-y-4">
            {loading && (
              <div className="text-center text-[12px] text-[#A1A1AA] py-4">Caricamento cronologia…</div>
            )}
            {messages.map((m, i) => (
              <div key={i} data-testid={`msg-${i}`} className={`flex gap-3 ${m.role === "user" ? "flex-row-reverse" : ""}`}>
                <div className={`w-7 h-7 rounded-md flex items-center justify-center shrink-0 ${m.role === "user" ? "bg-[#0A192F]" : "bg-[#FF5A00]"}`}>
                  {m.role === "user" ? <span className="text-white text-[12px] font-bold">TU</span> : <Sparkles className="w-3.5 h-3.5 text-white" />}
                </div>
                <div className={`max-w-[80%] flex flex-col gap-2 ${m.role === "user" ? "items-end" : "items-start"}`}>
                  <div className={`rounded-md p-3 text-[14px] leading-relaxed whitespace-pre-wrap font-mono ${m.role === "user" ? "bg-[#0A192F] text-white" : "bg-[#F9F9F8] border border-[#E4E4E1]"}`}>
                    {m.text}
                  </div>
                  {(m.pendingActions || []).map((action, actionIdx) => (
                    <div key={action.log_id} className="w-full max-w-sm">
                      <AIActionConfirm
                        action={action}
                        busy={executingKey === `${i}-${actionIdx}`}
                        onConfirm={(resolved) => confirmAction(i, actionIdx, resolved)}
                        onCancel={() => cancelAction(i, actionIdx)}
                      />
                    </div>
                  ))}
                </div>
              </div>
            ))}
            {listening && (
              <div className="flex gap-3">
                <div className="w-7 h-7 rounded-md flex items-center justify-center bg-[#FF5A00]"><Mic className="w-3.5 h-3.5 text-white animate-pulse" /></div>
                <div className="bg-[#FF5A0010] border border-[#FF5A0030] rounded-md p-3 font-mono text-[13px] text-[#FF5A00]">In ascolto… parla ora</div>
              </div>
            )}
            {speaking && !listening && (
              <div className="flex gap-3">
                <div className="w-7 h-7 rounded-md flex items-center justify-center bg-[#059669]"><Volume2 className="w-3.5 h-3.5 text-white animate-pulse" /></div>
                <div className="bg-[#05966910] border border-[#05966930] rounded-md p-3 font-mono text-[13px] text-[#059669]">L'AI sta parlando… <button onClick={stopSpeaking} className="underline ml-1">interrompi</button></div>
              </div>
            )}
            {busy && (
              <div className="flex gap-3">
                <div className="w-7 h-7 rounded-md flex items-center justify-center bg-[#FF5A00]"><Sparkles className="w-3.5 h-3.5 text-white animate-pulse" /></div>
                <div className="bg-[#F9F9F8] border border-[#E4E4E1] rounded-md p-3 font-mono text-[13px] text-[#A1A1AA]">sto analizzando i tuoi dati…</div>
              </div>
            )}
            <div ref={endRef} />
          </div>

          {/* Quick prompts */}
          <div className="border-t border-[#E4E4E1] p-3 flex flex-wrap gap-2">
            {quickPrompts.map(p => (
              <button key={p} onClick={() => send(p)} className="text-[11px] font-mono uppercase tracking-widest border border-[#E4E4E1] px-2 py-1 rounded hover:border-[#FF5A00] hover:text-[#FF5A00]">{p}</button>
            ))}
          </div>

          {/* Input */}
          <form onSubmit={(e) => { e.preventDefault(); send(input); }} className="border-t border-[#E4E4E1] p-3 flex gap-2">
            <input data-testid="ai-input" value={input} onChange={(e) => setInput(e.target.value)}
              placeholder={listening ? "Sto ascoltando…" : "Chiedi all'assistente o usa il microfono…"}
              className={`flex-1 bg-white border rounded-md px-3 py-2 text-[13px] focus:outline-none transition-colors ${listening ? "border-[#FF5A00] bg-[#FF5A0005]" : "border-[#E4E4E1] focus:border-[#0A192F]"}`} />
            {/* Bottone microfono */}
            <button type="button" onClick={toggleListening}
              className={`px-3 py-2 rounded-md text-[13px] font-medium transition-all ${listening ? "bg-[#FF5A00] text-white animate-pulse" : "border border-[#E4E4E1] text-[#52525B] hover:border-[#FF5A00] hover:text-[#FF5A00]"}`}
              title={listening ? "Clicca per fermare" : "Parla con l'AI"}>
              {listening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
            </button>
            {/* Stop audio */}
            {speaking && (
              <button type="button" onClick={stopSpeaking}
                className="px-3 py-2 bg-[#0A192F] text-white rounded-md animate-pulse"
                title="Interrompi lettura">
                <VolumeX className="w-4 h-4" />
              </button>
            )}
            <button data-testid="ai-send" disabled={busy} className="px-4 py-2 bg-[#0A192F] text-white rounded-md text-[13px] font-medium disabled:opacity-50">
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>

        {/* Suggestions panel */}
        <div className="bg-white border border-[#E4E4E1] rounded-md p-4 h-fit">
          <div className="flex items-center gap-2 mb-3">
            <Lightbulb className="w-4 h-4 text-[#FF5A00]" />
            <div className="font-mono text-[10px] uppercase tracking-widest text-[#52525B]">Clienti suggeriti</div>
          </div>
          {suggestions.length === 0 && <div className="text-[12px] text-[#A1A1AA] py-4 text-center">Generazione suggerimenti…</div>}
          <div className="space-y-3">
            {suggestions.map((s, i) => (
              <div key={i} className="border border-[#E4E4E1] rounded-md p-3">
                <div className="flex items-center justify-between mb-1">
                  <div className="font-cabinet font-bold text-[13px] flex-1 min-w-0 truncate">{s.client}</div>
                  <span className="font-mono text-[9px] uppercase tracking-widest px-1.5 py-0.5 rounded ml-2 shrink-0"
                    style={{ background: s.priority === "alta" ? "#FF5A0020" : "#F3F3F1", color: s.priority === "alta" ? "#FF5A00" : "#52525B" }}>
                    {s.priority}
                  </span>
                </div>
                <div className="text-[11px] text-[#52525B] leading-relaxed">{s.reason}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
