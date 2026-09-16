import { useEffect, useRef, useState } from "react";
import { Sparkles, Send, X, MessageCircle } from "lucide-react";

import { sendPublicAiMessage } from "../api/publicAi";
import { trackEvent } from "../lib/analytics";

const WELCOME = {
  role: "assistant",
  text: "Ciao! Chiedimi qualsiasi cosa su SalesFly: prezzi, funzionalità, come funziona la prova gratuita.",
};

// Solo gli ultimi messaggi vengono mandati al backend come contesto (vedi
// PUBLIC_CHAT_HISTORY_MAX_MESSAGES lato backend) — nessuno storico persistito,
// la conversazione vive solo nello stato di questo componente.
const MAX_HISTORY = 6;

// Widget flottante in basso a destra (stesso z-40 e offset di
// VoiceAssistant.jsx, l'unico altro elemento fisso in quella posizione
// nell'app autenticata) invece di una sezione dentro il flusso della
// pagina: il pannello messaggi è montato SOLO quando aperto, così
// l'useEffect di scroll-to-bottom non parte più al caricamento della
// homepage (bug: scrollIntoView sul primo mount trascinava giù l'intera
// pagina fino al widget, non solo il suo contenitore interno).
export default function PublicAiChat() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([WELCOME]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [messages, open]);

  const toggleOpen = () => {
    setOpen((o) => {
      const next = !o;
      if (next) trackEvent("public_ai_chat_opened");
      return next;
    });
  };

  const send = async () => {
    const text = input.trim();
    if (!text || busy) return;

    const history = messages
      .slice(-MAX_HISTORY)
      .map(({ role, text: t }) => ({ role, text: t }));

    setMessages((m) => [...m, { role: "user", text }]);
    setInput("");
    setBusy(true);
    trackEvent("public_ai_chat_message_sent");
    try {
      const data = await sendPublicAiMessage({ message: text, history });
      setMessages((m) => [...m, { role: "assistant", text: data.response }]);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      const errMsg =
        typeof detail === "string"
          ? detail
          : "Non sono riuscito a rispondere, riprova tra poco.";
      setMessages((m) => [...m, { role: "assistant", text: errMsg }]);
    } finally {
      setBusy(false);
    }
  };

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="fixed z-40 bottom-20 md:bottom-6 right-4 md:right-6 flex flex-col items-end gap-3">
      {open && (
        <div className="w-[calc(100vw-2rem)] max-w-[360px] h-[480px] max-h-[70vh] flex flex-col border border-[#E4E4E1] rounded-xl bg-[#F9F9F8] shadow-2xl overflow-hidden">
          <div className="flex items-center gap-2 px-4 py-3 bg-white border-b border-[#E4E4E1]">
            <div className="w-7 h-7 rounded-md bg-[#B23E00] flex items-center justify-center shrink-0">
              <Sparkles className="w-3.5 h-3.5 text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-cabinet font-bold text-[14px]">Chiedi a SalesFly</div>
              <div className="text-[11px] text-[#6B6B72] truncate">
                Assistente informativo, non collegato al tuo CRM
              </div>
            </div>
            <button
              type="button"
              onClick={toggleOpen}
              aria-label="Chiudi"
              className="w-7 h-7 shrink-0 rounded-md flex items-center justify-center text-[#6B6B72] hover:bg-[#F9F9F8]"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto px-4 py-3 flex flex-col gap-3">
            {messages.map((m, i) => (
              <div
                key={i}
                className={`flex gap-2 ${m.role === "user" ? "flex-row-reverse" : ""}`}
              >
                <div
                  className={`max-w-[85%] rounded-md px-3 py-2 text-[13px] leading-relaxed whitespace-pre-wrap ${
                    m.role === "user"
                      ? "bg-[#0A192F] text-white"
                      : "bg-white border border-[#E4E4E1]"
                  }`}
                >
                  {m.text}
                </div>
              </div>
            ))}
            {busy && (
              <div className="text-[12px] text-[#6B6B72] px-1">Sto scrivendo…</div>
            )}
            <div ref={endRef} />
          </div>

          <div className="flex items-center gap-2 px-3 py-3 bg-white border-t border-[#E4E4E1]">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              disabled={busy}
              placeholder="Es. quanto costa il piano Pro?"
              className="flex-1 min-w-0 text-[13px] px-3 py-2 rounded-md border border-[#E4E4E1] outline-none focus:border-[#B23E00] disabled:opacity-60"
            />
            <button
              type="button"
              onClick={send}
              disabled={busy || !input.trim()}
              className="w-9 h-9 shrink-0 rounded-md bg-[#0A192F] text-white flex items-center justify-center disabled:opacity-40"
              aria-label="Invia"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      <button
        type="button"
        onClick={toggleOpen}
        aria-label={open ? "Chiudi la chat" : "Apri la chat con SalesFly"}
        className="w-14 h-14 rounded-full bg-[#B23E00] text-white flex items-center justify-center shadow-lg hover:brightness-110 transition"
      >
        {open ? <X className="w-6 h-6" /> : <MessageCircle className="w-6 h-6" />}
      </button>
    </div>
  );
}
