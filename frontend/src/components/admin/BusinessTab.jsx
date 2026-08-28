import { useEffect, useState } from "react";
import { getAdminStats, listAdminUsers, updateAdminUser, deleteAdminUser, impersonateUser } from "../../api/admin";
import { Users, TrendingUp, CreditCard, Pencil, Trash2, Check, X, Eye, LogIn, ToggleLeft } from "lucide-react";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../ui/dialog";
import { fmt, STATUS_COLOR, IMPERSONATE_CATEGORIES, MODULES, EXTRA_MODULES } from "./constants";

// ---------------------------------------------------------------------
// Business: statistiche abbonamenti + lista utenti
// ---------------------------------------------------------------------
export default function BusinessTab() {
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [editUser, setEditUser] = useState(null);
  const [search, setSearch] = useState("");
  const [impersonateTarget, setImpersonateTarget] = useState(null); // { id, email, mode }
  const [impersonateCategory, setImpersonateCategory] = useState("");
  const [impersonateReason, setImpersonateReason] = useState("");
  const [submittingImpersonate, setSubmittingImpersonate] = useState(false);
  const [moduleTarget, setModuleTarget] = useState(null); // { id, email, disabled_modules, enabled_extra_modules }

  const load = async () => {
    const [s, u] = await Promise.all([
      getAdminStats(),
      listAdminUsers(page, 50),
    ]);
    setStats(s);
    setUsers(u.users);
    setTotal(u.total);
  };

  useEffect(() => { load(); }, [page]);

  const updateUser = async (id, payload) => {
    await updateAdminUser(id, payload);
    toast.success("Utente aggiornato");
    setEditUser(null);
    load();
  };

  const deleteUser = async (id, email) => {
    if (!window.confirm(`Eliminare l'utente ${email}?`)) return;
    await deleteAdminUser(id);
    toast.success("Utente eliminato");
    load();
  };

  // Reload pieno (non un semplice navigate): il cookie di sessione è già
  // stato sostituito dal server, serve ricaricare tutto lo stato dell'app
  // (AuthContext, mandanti, ecc.) come per un vero login.
  const goToImpersonatedApp = () => { window.location.href = "/app"; };

  const toggleModule = (value) => {
    setModuleTarget((prev) => {
      const has = prev.disabled_modules.includes(value);
      return {
        ...prev,
        disabled_modules: has
          ? prev.disabled_modules.filter((m) => m !== value)
          : [...prev.disabled_modules, value],
      };
    });
  };

  // Logica opposta a toggleModule sopra: qui "acceso" significa presente
  // nell'elenco (vedi EXTRA_MODULES/core.security.EXTRA_MODULE_KEYS,
  // spenti di default per tutti).
  const toggleExtraModule = (value) => {
    setModuleTarget((prev) => {
      const has = prev.enabled_extra_modules.includes(value);
      return {
        ...prev,
        enabled_extra_modules: has
          ? prev.enabled_extra_modules.filter((m) => m !== value)
          : [...prev.enabled_extra_modules, value],
      };
    });
  };

  const saveModules = async () => {
    await updateUser(moduleTarget.id, {
      disabled_modules: moduleTarget.disabled_modules,
      enabled_extra_modules: moduleTarget.enabled_extra_modules,
    });
    setModuleTarget(null);
  };

  const openImpersonateDialog = (u, mode) => {
    setImpersonateCategory("");
    setImpersonateReason("");
    setImpersonateTarget({ id: u.id, email: u.email, mode });
  };

  const submitImpersonate = async () => {
    if (!impersonateCategory) {
      toast.error("Indica una categoria per l'accesso");
      return;
    }
    if (impersonateTarget.mode === "edit" && !impersonateReason.trim()) {
      toast.error("Indica un motivo per accedere in modifica");
      return;
    }
    setSubmittingImpersonate(true);
    try {
      await impersonateUser(impersonateTarget.id, {
        mode: impersonateTarget.mode,
        category: impersonateCategory,
        reason: impersonateTarget.mode === "edit" ? impersonateReason.trim() : undefined,
      });
      goToImpersonatedApp();
    } catch {
      toast.error("Impossibile entrare nell'account di questo utente");
      setSubmittingImpersonate(false);
    }
  };

  const filtered = users.filter(u =>
    !search || u.email.includes(search) || u.name?.toLowerCase().includes(search.toLowerCase())
  );

  if (!stats) return <div className="p-8 text-center text-[#6B6B72]">Caricamento…</div>;

  return (
    <>
      {/* KPI */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {[
          { label: "Utenti totali", value: stats.total_users, icon: Users, color: "#0A192F" },
          { label: "Abbonati attivi", value: stats.active, icon: Check, color: "#059669" },
          { label: "In prova", value: stats.trial, icon: TrendingUp, color: "#B23E00" },
          { label: "MRR", value: fmt(stats.mrr), icon: CreditCard, color: "#059669" },
        ].map(k => (
          <div key={k.label} className="bg-white border border-[#E4E4E1] rounded-md p-5">
            <div className="font-mono text-[10px] uppercase tracking-widest text-[#6B6B72] mb-2">{k.label}</div>
            <div className="font-cabinet font-black text-2xl" style={{ color: k.color }}>{k.value}</div>
          </div>
        ))}
      </div>

      {/* Piano breakdown */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-white border border-[#E4E4E1] rounded-md p-4">
          <div className="font-mono text-[10px] uppercase tracking-widest text-[#6B6B72] mb-1">Piano Base</div>
          <div className="font-cabinet font-black text-xl">{stats.plan_base}</div>
          <div className="text-[11px] text-[#52525B]">{fmt(stats.plan_base * 6)}/mese</div>
        </div>
        <div className="bg-white border border-[#E4E4E1] rounded-md p-4">
          <div className="font-mono text-[10px] uppercase tracking-widest text-[#6B6B72] mb-1">Piano Pro</div>
          <div className="font-cabinet font-black text-xl text-[#B23E00]">{stats.plan_pro}</div>
          <div className="text-[11px] text-[#52525B]">{fmt(stats.plan_pro * 11)}/mese</div>
        </div>
        <div className="bg-white border border-[#E4E4E1] rounded-md p-4">
          <div className="font-mono text-[10px] uppercase tracking-widest text-[#6B6B72] mb-1">Cancellati</div>
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
                        style={{ background: u.plan === "pro" ? "#B23E0015" : "#0A192F15", color: u.plan === "pro" ? "#B23E00" : "#0A192F" }}>
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
                      <span className="font-mono text-[10px] uppercase tracking-widest" style={{ color: STATUS_COLOR[u.subscription_status] || "#6B6B72" }}>
                        {u.subscription_status || "trial"}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-[12px] text-[#6B6B72]">{u.created_at?.slice(0, 10)}</td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1">
                      {editUser?.id === u.id ? (
                        <>
                          <button onClick={() => updateUser(u.id, { plan: editUser.plan, subscription_status: editUser.subscription_status })}
                            className="p-1.5 text-[#059669] hover:bg-green-50 rounded"><Check className="w-4 h-4" /></button>
                          <button onClick={() => setEditUser(null)}
                            className="p-1.5 text-[#6B6B72] hover:bg-[#F3F3F1] rounded"><X className="w-4 h-4" /></button>
                        </>
                      ) : (
                        <>
                          <button onClick={() => openImpersonateDialog(u, "view")} title="Visualizza come utente (sola lettura)" aria-label="Visualizza come utente (sola lettura)"
                            className="p-1.5 text-[#6B6B72] hover:text-[#B23E00] hover:bg-[#FFF3EC] rounded"><Eye className="w-4 h-4" /></button>
                          <button onClick={() => openImpersonateDialog(u, "edit")} title="Accedi e modifica" aria-label="Accedi e modifica"
                            className="p-1.5 text-[#6B6B72] hover:text-[#B23E00] hover:bg-[#FFF3EC] rounded"><LogIn className="w-4 h-4" /></button>
                          <button onClick={() => setEditUser({...u})} title="Modifica utente" aria-label="Modifica utente"
                            className="p-1.5 text-[#6B6B72] hover:text-[#0A192F] hover:bg-[#F3F3F1] rounded"><Pencil className="w-4 h-4" /></button>
                          <button onClick={() => setModuleTarget({ id: u.id, email: u.email, disabled_modules: u.disabled_modules || [], enabled_extra_modules: u.enabled_extra_modules || [] })} title="Moduli attivi" aria-label="Moduli attivi"
                            className="p-1.5 text-[#6B6B72] hover:text-[#0A192F] hover:bg-[#F3F3F1] rounded"><ToggleLeft className="w-4 h-4" /></button>
                          <button onClick={() => deleteUser(u.id, u.email)} title="Elimina utente" aria-label="Elimina utente"
                            className="p-1.5 text-[#6B6B72] hover:text-red-500 hover:bg-red-50 rounded"><Trash2 className="w-4 h-4" /></button>
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

      {/* Categoria obbligatoria in ENTRAMBE le modalità: anche la sola
      lettura non modifica nulla, ma deve comunque dichiarare almeno il
      motivo di massima nell'audit log. Il motivo testuale libero resta
      richiesto in aggiunta solo per "Accedi e modifica" (permessi di
      scrittura, vedi core.security.forbid_demo_write). */}
      <Dialog open={!!impersonateTarget} onOpenChange={(v) => !v && setImpersonateTarget(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle>{impersonateTarget?.mode === "edit" ? "Accedi e modifica" : "Visualizza come utente"}</DialogTitle></DialogHeader>
          {impersonateTarget && (
            <div className="space-y-3">
              <p className="text-[13px] text-[#52525B]">
                {impersonateTarget.mode === "edit" ? (
                  <>Entrerai nel gestionale di <strong>{impersonateTarget.email}</strong> con permessi di scrittura:
                  potrai creare, modificare ed eliminare i suoi dati come se fossi lui.</>
                ) : (
                  <>Entrerai nel gestionale di <strong>{impersonateTarget.email}</strong> in sola lettura:
                  non potrai modificare i suoi dati.</>
                )}
              </p>
              <div>
                <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Categoria dell'accesso</label>
                <select
                  value={impersonateCategory}
                  onChange={(e) => setImpersonateCategory(e.target.value)}
                  className="bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px] w-full"
                  autoFocus
                >
                  <option value="">Seleziona…</option>
                  {IMPERSONATE_CATEGORIES.map((c) => (
                    <option key={c.value} value={c.value}>{c.label}</option>
                  ))}
                </select>
              </div>
              {impersonateTarget.mode === "edit" && (
                <div>
                  <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Motivo dell'accesso</label>
                  <textarea
                    value={impersonateReason}
                    onChange={(e) => setImpersonateReason(e.target.value)}
                    rows={3}
                    placeholder="Es. richiesta telefonica: correggere l'ordine #123"
                    className="bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px] w-full"
                  />
                </div>
              )}
              <div className="flex justify-end gap-2">
                <button onClick={() => setImpersonateTarget(null)} className="px-4 py-2 border border-[#E4E4E1] rounded-md text-[13px] font-medium">
                  Annulla
                </button>
                <button onClick={submitImpersonate}
                  disabled={submittingImpersonate || !impersonateCategory || (impersonateTarget.mode === "edit" && !impersonateReason.trim())}
                  className="px-4 py-2 bg-[#0A192F] text-white rounded-md text-[13px] font-medium disabled:opacity-50">
                  {impersonateTarget.mode === "edit" ? "Accedi e modifica" : "Visualizza come utente"}
                </button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Moduli attivi per l'account: la lettura di dati "condivisi" fra
      pagine (clienti, mandanti, prodotti, offerte) resta sempre
      raggiungibile anche a modulo disattivato — solo la creazione/
      modifica/cancellazione viene bloccata, vedi core/security.py
      require_module nel backend per il perché. */}
      <Dialog open={!!moduleTarget} onOpenChange={(v) => !v && setModuleTarget(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle>Moduli attivi</DialogTitle></DialogHeader>
          {moduleTarget && (
            <div className="space-y-3">
              <p className="text-[13px] text-[#52525B]">
                Disattiva le funzioni non usate da <strong>{moduleTarget.email}</strong>: spariscono dal menu e non sono più modificabili.
              </p>
              <div className="grid grid-cols-2 gap-2">
                {MODULES.map((m) => {
                  const enabled = !moduleTarget.disabled_modules.includes(m.value);
                  return (
                    <button key={m.value} type="button" onClick={() => toggleModule(m.value)}
                      className={`flex items-center justify-between px-3 py-2 rounded-md border text-[12px] font-medium transition-colors ${
                        enabled ? "border-[#059669]/30 bg-[#059669]/5 text-[#059669]" : "border-[#E4E4E1] text-[#6B6B72]"
                      }`}>
                      {m.label}
                      {enabled ? <Check className="w-3.5 h-3.5" /> : <X className="w-3.5 h-3.5" />}
                    </button>
                  );
                })}
              </div>

              <p className="text-[13px] text-[#52525B] pt-2">
                Moduli extra, costruiti per un cliente specifico — spenti per tutti finché non li attivi qui:
              </p>
              <div className="grid grid-cols-1 gap-2">
                {EXTRA_MODULES.map((m) => {
                  const enabled = moduleTarget.enabled_extra_modules.includes(m.value);
                  return (
                    <button key={m.value} type="button" onClick={() => toggleExtraModule(m.value)}
                      className={`flex items-center justify-between px-3 py-2 rounded-md border text-[12px] font-medium transition-colors ${
                        enabled ? "border-[#B23E00]/30 bg-[#B23E00]/5 text-[#B23E00]" : "border-[#E4E4E1] text-[#6B6B72]"
                      }`}>
                      {m.label}
                      {enabled ? <Check className="w-3.5 h-3.5" /> : <X className="w-3.5 h-3.5" />}
                    </button>
                  );
                })}
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button onClick={() => setModuleTarget(null)} className="px-4 py-2 border border-[#E4E4E1] rounded-md text-[13px] font-medium">
                  Annulla
                </button>
                <button onClick={saveModules} className="px-4 py-2 bg-[#0A192F] text-white rounded-md text-[13px] font-medium">
                  Salva
                </button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
