import { useEffect, useState } from "react";
import api from "../api";
import { Users, TrendingUp, CreditCard, XCircle, Pencil, Trash2, Check, X } from "lucide-react";
import { toast } from "sonner";

const fmt = (n) => new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(n || 0);

const STATUS_COLOR = {
  active: "#059669", trial: "#FF5A00", cancelled: "#DC2626", expired: "#A1A1AA"
};

export default function Admin() {
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [editUser, setEditUser] = useState(null);
  const [search, setSearch] = useState("");

  const load = async () => {
    const [s, u] = await Promise.all([
      api.get("/admin/stats"),
      api.get(`/admin/users?page=${page}&limit=50`),
    ]);
    setStats(s.data);
    setUsers(u.data.users);
    setTotal(u.data.total);
  };

  useEffect(() => { load(); }, [page]);

  const updateUser = async (id, payload) => {
    await api.patch(`/admin/users/${id}`, payload);
    toast.success("Utente aggiornato");
    setEditUser(null);
    load();
  };

  const deleteUser = async (id, email) => {
    if (!window.confirm(`Eliminare l'utente ${email}?`)) return;
    await api.delete(`/admin/users/${id}`);
    toast.success("Utente eliminato");
    load();
  };

  const filtered = users.filter(u =>
    !search || u.email.includes(search) || u.name?.toLowerCase().includes(search.toLowerCase())
  );

  if (!stats) return <div className="p-8 text-center text-[#A1A1AA]">Caricamento…</div>;

  return (
    <div className="p-4 md:p-8">
      <div className="border-b border-[#E4E4E1] pb-6 mb-6">
        <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#FF5A00] mb-2">Pannello</div>
        <h1 className="font-cabinet font-black text-3xl md:text-4xl tracking-tight">Admin Dashboard</h1>
      </div>

      {/* KPI */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {[
          { label: "Utenti totali", value: stats.total_users, icon: Users, color: "#0A192F" },
          { label: "Abbonati attivi", value: stats.active, icon: Check, color: "#059669" },
          { label: "In prova", value: stats.trial, icon: TrendingUp, color: "#FF5A00" },
          { label: "MRR", value: fmt(stats.mrr), icon: CreditCard, color: "#059669" },
        ].map(k => (
          <div key={k.label} className="bg-white border border-[#E4E4E1] rounded-md p-5">
            <div className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA] mb-2">{k.label}</div>
            <div className="font-cabinet font-black text-2xl" style={{ color: k.color }}>{k.value}</div>
          </div>
        ))}
      </div>

      {/* Piano breakdown */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-white border border-[#E4E4E1] rounded-md p-4">
          <div className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA] mb-1">Piano Base</div>
          <div className="font-cabinet font-black text-xl">{stats.plan_base}</div>
          <div className="text-[11px] text-[#52525B]">{fmt(stats.plan_base * 6)}/mese</div>
        </div>
        <div className="bg-white border border-[#E4E4E1] rounded-md p-4">
          <div className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA] mb-1">Piano Pro</div>
          <div className="font-cabinet font-black text-xl text-[#FF5A00]">{stats.plan_pro}</div>
          <div className="text-[11px] text-[#52525B]">{fmt(stats.plan_pro * 11)}/mese</div>
        </div>
        <div className="bg-white border border-[#E4E4E1] rounded-md p-4">
          <div className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA] mb-1">Cancellati</div>
          <div className="font-cabinet font-black text-xl text-red-500">{stats.cancelled}</div>
        </div>
        <div className="bg-[#0A192F] text-white rounded-md p-4">
          <div className="font-mono text-[10px] uppercase tracking-widest text-white/50 mb-1">ARR stimato</div>
          <div className="font-cabinet font-black text-xl">{fmt(stats.arr)}</div>
        </div>
      </div>

      {/* Lista utenti */}
      <div className="bg-white border border-[#E4E4E1] rounded-md overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#E4E4E1]">
          <div className="font-mono text-[11px] uppercase tracking-widest text-[#52525B]">Utenti ({total})</div>
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Cerca email o nome…"
            className="border border-[#E4E4E1] rounded-md px-3 py-1.5 text-[12px] w-48" />
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-[#F3F3F1]">
              <tr className="text-left">
                {["Nome", "Email", "Piano", "Stato", "Registrato", "Azioni"].map(h => (
                  <th key={h} className="px-4 py-3 font-mono text-[10px] uppercase tracking-widest text-[#52525B]">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(u => (
                <tr key={u.id} className="border-t border-[#E4E4E1] hover:bg-[#F9F9F8]">
                  <td className="px-4 py-3 text-[13px] font-medium">{u.name || "—"}</td>
                  <td className="px-4 py-3 text-[13px] text-[#52525B]">{u.email}</td>
                  <td className="px-4 py-3">
                    {editUser?.id === u.id ? (
                      <select value={editUser.plan} onChange={e => setEditUser({...editUser, plan: e.target.value})}
                        className="border border-[#E4E4E1] rounded px-2 py-1 text-[12px]">
                        <option value="base">Base</option>
                        <option value="pro">Pro</option>
                      </select>
                    ) : (
                      <span className="font-mono text-[11px] uppercase tracking-widest px-2 py-1 rounded"
                        style={{ background: u.plan === "pro" ? "#FF5A0015" : "#0A192F15", color: u.plan === "pro" ? "#FF5A00" : "#0A192F" }}>
                        {u.plan || "base"}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {editUser?.id === u.id ? (
                      <select value={editUser.subscription_status} onChange={e => setEditUser({...editUser, subscription_status: e.target.value})}
                        className="border border-[#E4E4E1] rounded px-2 py-1 text-[12px]">
                        {["trial","active","cancelled","expired"].map(s => <option key={s} value={s}>{s}</option>)}
                      </select>
                    ) : (
                      <span className="font-mono text-[10px] uppercase tracking-widest" style={{ color: STATUS_COLOR[u.subscription_status] || "#A1A1AA" }}>
                        {u.subscription_status || "trial"}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-[12px] text-[#A1A1AA]">{u.created_at?.slice(0, 10)}</td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1">
                      {editUser?.id === u.id ? (
                        <>
                          <button onClick={() => updateUser(u.id, { plan: editUser.plan, subscription_status: editUser.subscription_status })}
                            className="p-1.5 text-[#059669] hover:bg-green-50 rounded"><Check className="w-4 h-4" /></button>
                          <button onClick={() => setEditUser(null)}
                            className="p-1.5 text-[#A1A1AA] hover:bg-[#F3F3F1] rounded"><X className="w-4 h-4" /></button>
                        </>
                      ) : (
                        <>
                          <button onClick={() => setEditUser({...u})}
                            className="p-1.5 text-[#A1A1AA] hover:text-[#0A192F] hover:bg-[#F3F3F1] rounded"><Pencil className="w-4 h-4" /></button>
                          <button onClick={() => deleteUser(u.id, u.email)}
                            className="p-1.5 text-[#A1A1AA] hover:text-red-500 hover:bg-red-50 rounded"><Trash2 className="w-4 h-4" /></button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {total > 50 && (
          <div className="flex justify-center gap-2 p-4 border-t border-[#E4E4E1]">
            <button disabled={page === 1} onClick={() => setPage(p => p - 1)} className="px-3 py-1.5 border border-[#E4E4E1] rounded text-[12px] disabled:opacity-40">←</button>
            <span className="px-3 py-1.5 text-[12px]">Pag. {page}</span>
            <button disabled={page * 50 >= total} onClick={() => setPage(p => p + 1)} className="px-3 py-1.5 border border-[#E4E4E1] rounded text-[12px] disabled:opacity-40">→</button>
          </div>
        )}
      </div>
    </div>
  );
}
