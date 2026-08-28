import { useEffect, useState } from "react";
import { getAuditLog } from "../../api/admin";

// ---------------------------------------------------------------------
// Audit log amministrativo
// ---------------------------------------------------------------------
const ACTION_LABELS = {
  make_admin: "Promozione ad admin",
  update_user: "Modifica utente",
  delete_user: "Eliminazione utente",
  impersonate_user: "Accesso come utente",
};

export default function AuditTab() {
  const [entries, setEntries] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const data = await getAuditLog(page, 50);
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
        Azioni amministrative ({total})
      </div>
      {loading ? (
        <div className="p-8 text-center text-[#6B6B72]">Caricamento…</div>
      ) : entries.length === 0 ? (
        <div className="p-8 text-center text-[13px] text-[#6B6B72]">Nessuna azione registrata</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-[#F3F3F1]">
              <tr className="text-left">
                {["Quando", "Chi", "Azione", "Su utente", "Dettagli"].map((h) => (
                  <th key={h} className="px-4 py-2 font-mono text-[10px] uppercase tracking-widest text-[#52525B]">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {entries.map((e, i) => (
                <tr key={i} className="border-t border-[#E4E4E1]">
                  <td className="px-4 py-2.5 text-[12px] font-mono text-[#6B6B72]">
                    {e.created_at ? new Date(e.created_at).toLocaleString("it-IT") : "—"}
                  </td>
                  <td className="px-4 py-2.5 text-[12px] font-medium">{e.actor}</td>
                  <td className="px-4 py-2.5 text-[12px]">{ACTION_LABELS[e.action] || e.action}</td>
                  <td className="px-4 py-2.5 text-[12px] text-[#52525B] font-mono">{e.target_user_id || "—"}</td>
                  <td className="px-4 py-2.5 text-[11px] text-[#6B6B72] font-mono">
                    {e.detail && Object.keys(e.detail).length > 0 ? JSON.stringify(e.detail) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {total > 50 && (
        <div className="flex justify-center gap-2 p-4 border-t border-[#E4E4E1]">
          <button disabled={page === 1} onClick={() => setPage(p => p - 1)} className="px-3 py-1.5 border border-[#E4E4E1] rounded text-[12px] disabled:opacity-40">←</button>
          <span className="px-3 py-1.5 text-[12px]">Pag. {page}</span>
          <button disabled={page * 50 >= total} onClick={() => setPage(p => p + 1)} className="px-3 py-1.5 border border-[#E4E4E1] rounded text-[12px] disabled:opacity-40">→</button>
        </div>
      )}
    </div>
  );
}
