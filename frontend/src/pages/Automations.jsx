import { useEffect, useState } from "react";
import api from "../api";
import { Plus, Trash2, Zap, Clock, CheckCircle2, AlertTriangle, History, Pencil } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "../components/ui/dialog";
import { Switch } from "../components/ui/switch";
import { toast } from "sonner";
import { formatDistanceToNow, parseISO, format } from "date-fns";
import { it } from "date-fns/locale";

const TRIGGERS = {
  offer_expiring: "Offerta in scadenza",
  no_visit_30d: "Cliente non visitato da 30 giorni",
  lead_inactive: "Lead inattivo",
};
const ACTIONS = {
  send_reminder: "Invia promemoria",
  create_task: "Crea task",
  send_email: "Invia email follow-up",
};

// Ogni trigger legge dal proprio 'config' un campo diverso (vedi
// backend/services/automation_engine.py::_eval_offer_expiring/_eval_no_visit_30d/_eval_lead_inactive):
// offer_expiring usa 'days_before', gli altri due usano 'days'. 'cooldown_days'
// è invece condiviso da tutti i trigger (facoltativo, ripete il promemoria dopo N
// giorni invece di eseguirlo una sola volta).
const DAYS_FIELD_BY_TRIGGER = {
  offer_expiring: "days_before",
  no_visit_30d: "days",
  lead_inactive: "days",
};
const DAYS_LABEL_BY_TRIGGER = {
  offer_expiring: "Giorni di preavviso prima della scadenza",
  no_visit_30d: "Giorni senza visita prima di considerare il cliente inattivo",
  lead_inactive: "Giorni di inattività prima di considerare il lead inattivo",
};
const DAYS_DEFAULT_BY_TRIGGER = {
  offer_expiring: 3,
  no_visit_30d: 30,
  lead_inactive: 7,
};

export default function Automations() {
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [historyFor, setHistoryFor] = useState(null);

  const load = async () => { const { data } = await api.get("/automations"); setItems(data); };
  useEffect(() => { load(); }, []);

  const toggle = async (a) => {
    await api.put(`/automations/${a.id}`, { ...a, enabled: !a.enabled });
    load();
  };

  return (
    <div className="p-4 md:p-8">
      <div className="flex items-end justify-between border-b border-[#E4E4E1] pb-6 mb-6">
        <div>
          <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#FF5A00] mb-2">Produttività</div>
          <h1 className="font-cabinet font-black text-3xl md:text-4xl tracking-tight">Automazioni</h1>
          <p className="text-[14px] text-[#52525B] mt-2">Riduci il lavoro manuale con regole automatiche.</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <button data-testid="new-automation-button" className="flex items-center gap-2 px-4 py-2.5 bg-[#0A192F] text-white rounded-md text-[13px] font-medium">
              <Plus className="w-4 h-4" /> Nuova regola
            </button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>Nuova automazione</DialogTitle></DialogHeader>
            <AutoForm onSave={async (f) => { await api.post("/automations", f); load(); toast.success("Regola creata"); setOpen(false); }} />
          </DialogContent>
        </Dialog>
      </div>

      <div className="space-y-3">
        {items.map(a => (
          <div key={a.id} data-testid={`automation-${a.id}`} className="bg-white border border-[#E4E4E1] rounded-md p-5">
            <div className="flex items-center gap-4">
              <div className={`w-10 h-10 rounded-md flex items-center justify-center shrink-0 ${a.enabled ? "bg-[#FF5A00]" : "bg-[#F3F3F1]"}`}>
                <Zap className={`w-5 h-5 ${a.enabled ? "text-white" : "text-[#A1A1AA]"}`} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-cabinet font-bold text-[15px]">{a.name}</div>
                <div className="text-[12px] text-[#52525B] mt-1">
                  <span className="font-mono uppercase tracking-widest text-[10px] text-[#FF5A00]">quando</span> {TRIGGERS[a.trigger] || a.trigger} →
                  <span className="font-mono uppercase tracking-widest text-[10px] text-[#0A192F] ml-1">allora</span> {ACTIONS[a.action] || a.action}
                </div>
                <ConfigSummary automation={a} />
              </div>
              <Switch checked={a.enabled} onCheckedChange={() => toggle(a)} data-testid={`toggle-automation-${a.id}`} />
              <button onClick={() => setEditing(a)} data-testid={`edit-automation-${a.id}`} className="text-[#A1A1AA] hover:text-[#0A192F]">
                <Pencil className="w-4 h-4" />
              </button>
              <button onClick={async () => { await api.delete(`/automations/${a.id}`); load(); }} className="text-[#A1A1AA] hover:text-[#DC2626]">
                <Trash2 className="w-4 h-4" />
              </button>
            </div>

            <LastRunSummary automation={a} onShowHistory={() => setHistoryFor(a)} />
          </div>
        ))}
        {items.length === 0 && (
          <div className="bg-white border border-[#E4E4E1] rounded-md p-8 text-center text-[13px] text-[#A1A1AA]">
            Nessuna automazione configurata.
          </div>
        )}
      </div>

      {editing && (
        <Dialog open onOpenChange={(v) => !v && setEditing(null)}>
          <DialogContent>
            <DialogHeader><DialogTitle>Modifica automazione</DialogTitle></DialogHeader>
            <AutoForm
              initial={editing}
              onSave={async (f) => {
                await api.put(`/automations/${editing.id}`, f);
                load();
                toast.success("Regola aggiornata");
                setEditing(null);
              }}
            />
          </DialogContent>
        </Dialog>
      )}

      {historyFor && <RunHistoryDialog automation={historyFor} onClose={() => setHistoryFor(null)} />}
    </div>
  );
}

function ConfigSummary({ automation: a }) {
  const daysField = DAYS_FIELD_BY_TRIGGER[a.trigger];
  const daysValue = a.config?.[daysField];
  const cooldown = a.config?.cooldown_days;
  const runAt = a.config?.run_at;
  const hasCustomEmail = !!(a.config?.email_subject || a.config?.email_message);
  const isTask = a.action === "create_task";
  if (daysValue == null && !cooldown && !runAt && !hasCustomEmail && !isTask) return null;
  return (
    <div className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA] mt-1">
      {daysValue != null && `${daysValue} giorni`}
      {cooldown ? ` · si ripete ogni ${cooldown} giorni` : ""}
      {runAt ? ` · ore ${runAt}` : ""}
      {hasCustomEmail ? " · email personalizzata" : ""}
      {isTask ? ` · task tra ${a.config?.task_delay_days ?? 1}g alle ${a.config?.task_time || "09:00"}` : ""}
    </div>
  );
}

function LastRunSummary({ automation: a, onShowHistory }) {
  if (!a.last_run_at) {
    return (
      <div className="mt-3 pt-3 border-t border-[#F3F3F1] text-[11px] text-[#A1A1AA] font-mono uppercase tracking-widest">
        Ancora nessuna esecuzione — la regola verrà valutata al prossimo ciclo (ogni 10 minuti)
      </div>
    );
  }
  const hasErrors = (a.last_run_errors || 0) > 0;
  return (
    <div className="mt-3 pt-3 border-t border-[#F3F3F1] flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[12px]">
      <span className="flex items-center gap-1.5 text-[#52525B]">
        <Clock className="w-3.5 h-3.5 shrink-0" />
        Ultima esecuzione: {formatDistanceToNow(parseISO(a.last_run_at), { addSuffix: true, locale: it })}
      </span>
      <span className={`flex items-center gap-1.5 ${hasErrors ? "text-[#DC2626]" : "text-[#059669]"}`}>
        {hasErrors ? <AlertTriangle className="w-3.5 h-3.5 shrink-0" /> : <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />}
        {(a.last_run_executed || 0)} azioni eseguite
        {(a.last_run_skipped || 0) > 0 && ` · ${a.last_run_skipped} saltate`}
        {hasErrors && ` · ${a.last_run_errors} errori`}
      </span>
      {a.last_run_error && (
        <span className="text-[#DC2626] italic truncate max-w-full" title={a.last_run_error}>
          {a.last_run_error}
        </span>
      )}
      <button
        onClick={onShowHistory}
        data-testid={`automation-history-${a.id}`}
        className="ml-auto flex items-center gap-1 font-mono uppercase tracking-widest text-[10px] text-[#52525B] hover:text-[#0A0A0A]"
      >
        <History className="w-3.5 h-3.5" /> storico esecuzioni
      </button>
    </div>
  );
}

function RunHistoryDialog({ automation, onClose }) {
  const [runs, setRuns] = useState(null);

  useEffect(() => {
    api.get(`/automations/${automation.id}/runs`).then(({ data }) => setRuns(data));
  }, [automation.id]);

  return (
    <Dialog open onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center justify-between gap-4 pr-6">
            <span>Storico · {automation.name}</span>
          </DialogTitle>
        </DialogHeader>

        <div className="max-h-[60vh] overflow-y-auto -mx-1 px-1">
          {runs === null && <div className="text-[13px] text-[#A1A1AA] py-6 text-center">caricamento…</div>}
          {runs && runs.length === 0 && (
            <div className="text-[13px] text-[#A1A1AA] py-6 text-center">Nessuna esecuzione registrata per questa regola.</div>
          )}
          {runs && runs.length > 0 && (
            <div className="space-y-2">
              {runs.map((r) => (
                <div key={`${r.automation_id}-${r.target_id}`} data-testid={`run-${r.target_id}`}
                     className="border border-[#E4E4E1] rounded-md p-3 text-[12px]">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono uppercase tracking-widest text-[10px] text-[#A1A1AA]">{r.target_type}</span>
                    <span className={`font-mono uppercase tracking-widest text-[10px] px-1.5 py-0.5 rounded ${
                      r.status === "ok" ? "bg-[#05966915] text-[#059669]"
                        : r.status === "failed_permanent" ? "bg-[#DC262615] text-[#DC2626]"
                        : "bg-[#FF5A0015] text-[#FF5A00]"
                    }`}>
                      {r.status === "ok" ? "riuscita" : r.status === "failed_permanent" ? "fallita definitivamente" : "in errore"}
                    </span>
                  </div>
                  {r.updated_at && (
                    <div className="text-[#52525B] mt-1">
                      {format(parseISO(r.updated_at), "d MMM yyyy, HH:mm", { locale: it })}
                      {r.attempts > 0 && ` · ${r.attempts} tentativo/i`}
                    </div>
                  )}
                  {r.last_error && <div className="text-[#DC2626] mt-1 italic">{r.last_error}</div>}
                </div>
              ))}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

function AutoForm({ initial, onSave }) {
  const [f, setF] = useState(() => initial
    ? { ...initial, config: { ...(initial.config || {}) } }
    : { name: "", trigger: "offer_expiring", action: "send_reminder", enabled: true, config: {} }
  );

  const daysField = DAYS_FIELD_BY_TRIGGER[f.trigger];
  const daysValue = f.config?.[daysField] ?? DAYS_DEFAULT_BY_TRIGGER[f.trigger];
  const cooldownValue = f.config?.cooldown_days ?? "";
  const sendsEmail = f.action === "send_reminder" || f.action === "send_email";
  const createsTask = f.action === "create_task";

  const setTrigger = (trigger) => {
    // Cambiando trigger cambia solo la chiave del campo "giorni"
    // (days_before vs days, si riparte dal default del nuovo trigger): le
    // altre opzioni (cooldown, email personalizzata, orario) sono
    // indipendenti dal trigger e restano quelle già impostate.
    const { [DAYS_FIELD_BY_TRIGGER[f.trigger]]: _drop, ...rest } = f.config || {};
    setF({ ...f, trigger, config: rest });
  };

  const setDays = (value) => {
    const n = value === "" ? undefined : Number(value);
    setF({ ...f, config: { ...f.config, [daysField]: n } });
  };

  const setCooldown = (value) => {
    const n = value === "" ? undefined : Number(value);
    setF({ ...f, config: { ...f.config, cooldown_days: n } });
  };

  const setConfigText = (key, value) => {
    setF({ ...f, config: { ...f.config, [key]: value || undefined } });
  };

  const setConfigNumber = (key, value) => {
    const n = value === "" ? undefined : Number(value);
    setF({ ...f, config: { ...f.config, [key]: n } });
  };

  return (
    <form onSubmit={async (e) => { e.preventDefault(); await onSave(f); }} className="space-y-3">
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Nome regola *</label>
        <input required value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })}
               className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
        <p className="text-[11px] text-[#A1A1AA] mt-1">
          {sendsEmail && !f.config?.email_subject
            ? "Usato anche come oggetto dell'email, se non imposti un oggetto personalizzato qui sotto."
            : ""}
        </p>
      </div>
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Trigger</label>
        <select value={f.trigger} onChange={(e) => setTrigger(e.target.value)}
                className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]">
          {Object.entries(TRIGGERS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </div>
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">
          {DAYS_LABEL_BY_TRIGGER[f.trigger]}
        </label>
        <input
          type="number" min={1} step={1}
          data-testid="automation-days-input"
          value={daysValue ?? ""}
          onChange={(e) => setDays(e.target.value)}
          placeholder={String(DAYS_DEFAULT_BY_TRIGGER[f.trigger])}
          className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]"
        />
      </div>
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">
          Ripeti il promemoria dopo (giorni, facoltativo)
        </label>
        <input
          type="number" min={1} step={1}
          data-testid="automation-cooldown-input"
          value={cooldownValue}
          onChange={(e) => setCooldown(e.target.value)}
          placeholder="mai (una sola volta per elemento)"
          className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]"
        />
      </div>
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Azione</label>
        <select value={f.action} onChange={(e) => setF({ ...f, action: e.target.value })}
                className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]">
          {Object.entries(ACTIONS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </div>

      {createsTask && (
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">
              Orario del task
            </label>
            <input
              type="time"
              data-testid="automation-task-time-input"
              value={f.config?.task_time || "09:00"}
              onChange={(e) => setConfigText("task_time", e.target.value)}
              className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]"
            />
          </div>
          <div>
            <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">
              Giorni di ritardo
            </label>
            <input
              type="number" min={0} step={1}
              data-testid="automation-task-delay-input"
              value={f.config?.task_delay_days ?? 1}
              onChange={(e) => setConfigNumber("task_delay_days", e.target.value)}
              className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]"
            />
          </div>
          <p className="text-[11px] text-[#A1A1AA] col-span-2">
            Il task viene piazzato a quest'ora (fuso orario italiano), i giorni di ritardo dopo il rilevamento della condizione.
          </p>
        </div>
      )}

      {sendsEmail && (
        <>
          <div>
            <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">
              Oggetto email personalizzato (facoltativo)
            </label>
            <input
              data-testid="automation-email-subject-input"
              value={f.config?.email_subject || ""}
              onChange={(e) => setConfigText("email_subject", e.target.value)}
              placeholder={f.name || "usa il nome della regola"}
              className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]"
            />
          </div>
          <div>
            <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">
              Contenuto email personalizzato (facoltativo)
            </label>
            <textarea
              rows={3}
              data-testid="automation-email-message-input"
              value={f.config?.email_message || ""}
              onChange={(e) => setConfigText("email_message", e.target.value)}
              placeholder="es. Ciao {nome}, non ti vediamo da un po'…"
              className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]"
            />
            <p className="text-[11px] text-[#A1A1AA] mt-1">
              Puoi usare <code>{"{nome}"}</code>{f.trigger === "offer_expiring" ? <>, <code>{"{scadenza}"}</code></> : <>, <code>{"{citta}"}</code></>} — vengono sostituiti con i dati reali.
            </p>
          </div>
        </>
      )}

      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Orario di esecuzione (facoltativo)</label>
        <input
          type="time"
          data-testid="automation-run-at-input"
          value={f.config?.run_at || ""}
          onChange={(e) => setConfigText("run_at", e.target.value)}
          className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]"
        />
        <p className="text-[11px] text-[#A1A1AA] mt-1">
          Se impostato, la regola viene valutata una volta al giorno a quest'ora invece che ad ogni ciclo (ogni 10 minuti).
        </p>
      </div>

      <button data-testid="save-automation-button" type="submit" className="w-full bg-[#0A192F] text-white py-2.5 rounded-md text-[13px] font-medium">
        {initial ? "Salva modifiche" : "Salva regola"}
      </button>
    </form>
  );
}
