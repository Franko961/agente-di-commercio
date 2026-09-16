import { useEffect, useState } from "react";
import { getPublicAiChatLogs } from "../../api/admin";

const LIMIT = 50;

// ---------------------------------------------------------------------
// Domande fatte al widget AI pubblico della homepage (vedi
// PublicAiChat.jsx / routers/public_ai.py) — nessuno storico per utente,
// solo domanda/risposta/timestamp: serve a vedere di cosa chiedono
// davvero i visitatori, stesso spirito della ricerca keyword.
// ---------------------------------------------------------------------
export default function PublicAiChatTab() {
  const [entries, setEntries] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const data = await getPublicAiChatLogs(page, LIMIT);
      setEntries(data.entries);
      setTotal(data.total);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [page]);

  return (
    <div className="bg-white border border-[#E4E4E1] rounded-md overflow-hidden">
      <div className="px-4 py-3 border-b border-[#E4E4E1] font-mono text-[11px] uppercase tracking-widest text-[#52525B]">
        Domande alla chat AI pubblica ({total})
      </div>
      {loading ? (
        <div className="p-8 text-center text-[#6B6B72]">Caricamento…</div>
      ) : entries.length === 0 ? (
        <div className="p-8 text-center text-[13px] text-[#6B6B72]">Nessuna domanda ricevuta</div>
      ) : (
        <div className="divide-y divide-[#E4E4E1]">
          {entries.map((e) => (
            <div key={e.id} className="p-4">
              <div className="text-[11px] font-mono text-[#6B6B72] mb-1.5">
                {e.created_at ? new Date(e.created_at).toLocaleString("it-IT") : "—"}
              </div>
              <div className="text-[13px] font-medium mb-1.5">{e.domanda}</div>
              <div className="text-[13px] text-[#52525B] whitespace-pre-wrap">{e.risposta}</div>
            </div>
          ))}
        </div>
      )}
      {total > LIMIT && (
        <div className="flex justify-center gap-2 p-4 border-t border-[#E4E4E1]">
          <button disabled={page === 1} onClick={() => setPage(p => p - 1)} className="px-3 py-1.5 border border-[#E4E4E1] rounded text-[12px] disabled:opacity-40">←</button>
          <span className="px-3 py-1.5 text-[12px]">Pag. {page}</span>
          <button disabled={page * LIMIT >= total} onClick={() => setPage(p => p + 1)} className="px-3 py-1.5 border border-[#E4E4E1] rounded text-[12px] disabled:opacity-40">→</button>
        </div>
      )}
    </div>
  );
}
