import { useEffect, useState } from "react";
import api from "../api";
import { Plus, Trash2, Zap } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "../components/ui/dialog";
import { Switch } from "../components/ui/switch";
import { toast } from "sonner";

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

export default function Automations() {
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(false);

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
          <div key={a.id} data-testid={`automation-${a.id}`} className="bg-white border border-[#E4E4E1] rounded-md p-5 flex items-center gap-4">
            <div className={`w-10 h-10 rounded-md flex items-center justify-center shrink-0 ${a.enabled ? "bg-[#FF5A00]" : "bg-[#F3F3F1]"}`}>
              <Zap className={`w-5 h-5 ${a.enabled ? "text-white" : "text-[#A1A1AA]"}`} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-cabinet font-bold text-[15px]">{a.name}</div>
              <div className="text-[12px] text-[#52525B] mt-1">
                <span className="font-mono uppercase tracking-widest text-[10px] text-[#FF5A00]">quando</span> {TRIGGERS[a.trigger] || a.trigger} →
                <span className="font-mono uppercase tracking-widest text-[10px] text-[#0A192F] ml-1">allora</span> {ACTIONS[a.action] || a.action}
              </div>
            </div>
            <Switch checked={a.enabled} onCheckedChange={() => toggle(a)} data-testid={`toggle-automation-${a.id}`} />
            <button onClick={async () => { await api.delete(`/automations/${a.id}`); load(); }} className="text-[#A1A1AA] hover:text-[#DC2626]">
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

function AutoForm({ onSave }) {
  const [f, setF] = useState({ name: "", trigger: "offer_expiring", action: "send_reminder", enabled: true, config: {} });
  return (
    <form onSubmit={async (e) => { e.preventDefault(); await onSave(f); }} className="space-y-3">
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Nome regola *</label>
        <input required value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })}
               className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
      </div>
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Trigger</label>
        <select value={f.trigger} onChange={(e) => setF({ ...f, trigger: e.target.value })}
                className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]">
          {Object.entries(TRIGGERS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </div>
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Azione</label>
        <select value={f.action} onChange={(e) => setF({ ...f, action: e.target.value })}
                className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]">
          {Object.entries(ACTIONS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </div>
      <button data-testid="save-automation-button" type="submit" className="w-full bg-[#0A192F] text-white py-2.5 rounded-md text-[13px] font-medium">Salva regola</button>
    </form>
  );
}
