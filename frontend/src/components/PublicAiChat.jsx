import { useEffect, useRef, useState } from "react";
import { Sparkles, Send } from "lucide-react";

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

export default function PublicAiChat() {
  const [messages, setMessages] = useState([WELCOME]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

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
    <div className="max-w-2xl mx-auto border border-[#E4E4E1] rounded-xl bg-[#F9F9F8] overflow-hidden">
      <div className="flex items-center gap-2 px-5 py-4 bg-white border-b border-[#E4E4E1]">
        <div className="w-7 h-7 rounded-md bg-[#B23E00] flex items-center justify-center shrink-0">
          <Sparkles className="w-3.5 h-3.5 text-white" />
        </div>
        <div>
          <div className="font-cabinet font-bold text-[14px]">Chiedi a SalesFly</div>
          <div className="text-[12px] text-[#6B6B72]">
            Assistente informativo: non è collegato al tuo CRM, risponde solo su SalesFly.
          </div>
        </div>
      </div>

      <div className="max-h-[360px] overflow-y-auto px-5 py-4 flex flex-col gap-3">
        {messages.map((m, i) => (
          <div
            key={i}
            className={`flex gap-2 ${m.role === "user" ? "flex-row-reverse" : ""}`}
          >
            <div
              className={`max-w-[80%] rounded-md px-3 py-2 text-[13px] leading-relaxed whitespace-pre-wrap ${
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

      <div className="flex items-center gap-2 px-4 py-3 bg-white border-t border-[#E4E4E1]">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={busy}
          placeholder="Es. quanto costa il piano Pro?"
          className="flex-1 text-[13px] px-3 py-2 rounded-md border border-[#E4E4E1] outline-none focus:border-[#B23E00] disabled:opacity-60"
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
  );
}
