import { useEffect, useState, useRef } from "react";
import api from "../api";
import { Sparkles, Send, Lightbulb, Trash2 } from "lucide-react";

const WELCOME = { role: "assistant", text: "Ciao! Sono il tuo assistente commerciale. Posso suggerirti i clienti più importanti da visitare, analizzare il fatturato e darti consigli pratici. Cosa vuoi sapere?" };

export default function AIAssistant() {
  const [messages, setMessages] = useState([WELCOME]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [suggestions, setSuggestions] = useState([]);
  const endRef = useRef(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  // Carica cronologia al mount
  useEffect(() => {
    const loadHistory = async () => {
      try {
        const { data } = await api.get("/ai/history");
        if (data && data.length > 0) {
          const history = data.flatMap(h => [
            { role: "user", text: h.message },
            { role: "assistant", text: h.response },
          ]);
          setMessages([WELCOME, ...history]);
        }
      } catch (e) {
        // nessuna storia, ok
      } finally {
        setLoading(false);
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
      const { data } = await api.post("/ai/chat", { message: text });
      // Mostra azioni CRM eseguite + risposta
      const actions = data.actions || [];
      let fullText = data.response;
      if (actions.length > 0) {
        fullText = actions.join("\n") + (data.response ? "\n\n" + data.response : "");
      }
      setMessages(m => [...m, { role: "assistant", text: fullText, actions }]);
    } catch (err) {
      setMessages(m => [...m, { role: "assistant", text: "Errore di comunicazione con l'AI. Riprova tra poco." }]);
    } finally {
      setBusy(false);
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
        <button onClick={clearHistory} className="flex items-center gap-2 px-3 py-2 border border-[#E4E4E1] hover:border-red-300 hover:text-red-500 rounded-md text-[12px] text-[#A1A1AA] transition-colors">
          <Trash2 className="w-3.5 h-3.5" /> Cancella chat
        </button>
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
                <div className={`max-w-[80%] rounded-md p-3 text-[14px] leading-relaxed whitespace-pre-wrap font-mono ${m.role === "user" ? "bg-[#0A192F] text-white" : "bg-[#F9F9F8] border border-[#E4E4E1]"}`}>
                  {m.text}
                </div>
              </div>
            ))}
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
            <input data-testid="ai-input" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Chiedi all'assistente…"
              className="flex-1 bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px] focus:outline-none focus:border-[#0A192F]" />
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
