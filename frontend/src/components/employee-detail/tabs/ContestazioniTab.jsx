import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { FileText, Upload, Plus, Pencil, Trash2 } from "lucide-react";
import {
  listDisciplinaryActions, createDisciplinaryAction, updateDisciplinaryAction,
  deleteDisciplinaryAction, uploadEmployeeDocument,
} from "../../../api/employees";
import { FILE_BASE, DOCUMENT_MAX_MB, formatApiError } from "../constants";

const CONTESTAZIONE_TYPE_LABELS = {
  richiamo_verbale: "Richiamo verbale", lettera_richiamo: "Lettera di richiamo",
  contestazione_disciplinare: "Contestazione disciplinare", sospensione: "Sospensione", altro: "Altro",
};
const CONTESTAZIONE_OUTCOME_LABELS = {
  in_attesa: "In attesa", archiviata: "Archiviata", accolta: "Accolta",
  sanzione_confermata: "Sanzione confermata", altro: "Altro",
};
const CONTESTAZIONE_OUTCOME_COLORS = {
  in_attesa: "#B23E00", archiviata: "#6B6B72", accolta: "#059669",
  sanzione_confermata: "#DC2626", altro: "#6B6B72",
};

export default function ContestazioniTab({ employeeId }) {
  const [items, setItems] = useState(null);
  const [formOpen, setFormOpen] = useState(false);
  const [editTarget, setEditTarget] = useState(null);

  const load = async () => {
    setItems(await listDisciplinaryActions(employeeId));
  };
  useEffect(() => { load(); }, [employeeId]); // eslint-disable-line react-hooks/exhaustive-deps

  const openNew = () => { setEditTarget(null); setFormOpen(true); };
  const openEdit = (item) => { setEditTarget(item); setFormOpen(true); };
  const closeForm = () => { setFormOpen(false); setEditTarget(null); };

  const remove = async (item) => {
    if (!window.confirm(`Eliminare la contestazione "${item.subject}"?`)) return;
    try {
      await deleteDisciplinaryAction(employeeId, item.id);
      toast.success("Contestazione eliminata");
      load();
    } catch {
      toast.error("Errore eliminazione");
    }
  };

  // Il record salva solo il document_id (vedi models/employee_disciplinary_action.py):
  // il download riusa l'endpoint dei documenti dipendente, stesso meccanismo di DocumentiTab.
  const download = async (item) => {
    try {
      const res = await fetch(`${FILE_BASE}/api/employees/${employeeId}/documents/${item.document_id}/download`, {
        credentials: "include",
      });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${item.subject || "contestazione"}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch {
      toast.error("Errore download");
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <span className="text-[13px] font-medium text-[#52525B]">Contestazioni disciplinari: {items ? items.length : "…"}</span>
        <button onClick={openNew} className="flex items-center gap-1.5 px-3 py-2 bg-[#0A192F] text-white rounded-md text-[12px] font-medium">
          <Plus className="w-3.5 h-3.5" /> Nuova contestazione
        </button>
      </div>
      {formOpen && (
        <ContestazioneForm employeeId={employeeId} initial={editTarget} onDone={() => { closeForm(); load(); }} onCancel={closeForm} />
      )}
      {items && items.length > 0 && (
        <div className="overflow-x-auto border border-[#E4E4E1] rounded-md">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="bg-[#F9F9F8] text-left font-mono text-[10px] uppercase tracking-widest text-[#6B6B72]">
                <th className="px-3 py-2">Data</th>
                <th className="px-3 py-2">Tipo</th>
                <th className="px-3 py-2">Oggetto</th>
                <th className="px-3 py-2">Stato</th>
                <th className="px-3 py-2">Documento</th>
                <th className="px-3 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {items.map((it) => (
                <tr key={it.id} className="border-t border-[#E4E4E1]">
                  <td className="px-3 py-2 whitespace-nowrap">{it.contestation_date}</td>
                  <td className="px-3 py-2 whitespace-nowrap">{CONTESTAZIONE_TYPE_LABELS[it.type] || it.type}</td>
                  <td className="px-3 py-2 max-w-xs truncate">{it.subject}</td>
                  <td className="px-3 py-2 whitespace-nowrap">
                    <span className="font-mono text-[10px] uppercase tracking-widest px-1.5 py-0.5 rounded-full"
                      style={{ background: `${CONTESTAZIONE_OUTCOME_COLORS[it.outcome]}1A`, color: CONTESTAZIONE_OUTCOME_COLORS[it.outcome] }}>
                      {CONTESTAZIONE_OUTCOME_LABELS[it.outcome] || it.outcome}
                    </span>
                  </td>
                  <td className="px-3 py-2 whitespace-nowrap">
                    {it.document_id ? (
                      <button onClick={() => download(it)} title="Scarica documento" aria-label="Scarica documento"
                        className="p-1 text-[#6B6B72] hover:text-[#0A192F] hover:bg-[#F3F3F1] rounded"><FileText className="w-4 h-4" /></button>
                    ) : <span className="text-[#6B6B72]">—</span>}
                  </td>
                  <td className="px-3 py-2 whitespace-nowrap">
                    <div className="flex gap-1 justify-end">
                      <button onClick={() => openEdit(it)} title="Modifica" aria-label="Modifica contestazione"
                        className="p-1.5 text-[#6B6B72] hover:text-[#0A192F] hover:bg-[#F3F3F1] rounded"><Pencil className="w-4 h-4" /></button>
                      <button onClick={() => remove(it)} title="Elimina" aria-label="Elimina contestazione"
                        className="p-1.5 text-[#6B6B72] hover:text-red-500 hover:bg-red-50 rounded"><Trash2 className="w-4 h-4" /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {items && items.length === 0 && !formOpen && (
        <div className="bg-white border border-[#E4E4E1] rounded-md p-6 text-center text-[#6B6B72] text-[13px]">Nessuna contestazione registrata.</div>
      )}
    </div>
  );
}

function ContestazioneForm({ employeeId, initial, onDone, onCancel }) {
  const fileRef = useRef(null);
  const [file, setFile] = useState(null);
  const [f, setF] = useState({
    type: initial?.type || "richiamo_verbale",
    subject: initial?.subject || "",
    description: initial?.description || "",
    event_date: initial?.event_date || "",
    contestation_date: initial?.contestation_date || new Date().toISOString().slice(0, 10),
    received_date: initial?.received_date || "",
    justification_deadline: initial?.justification_deadline || "",
    justification_submitted: initial?.justification_submitted || false,
    justification_date: initial?.justification_date || "",
    outcome: initial?.outcome || "in_attesa",
    sanction: initial?.sanction || "",
    notes: initial?.notes || "",
  });
  const [saving, setSaving] = useState(false);

  const onPick = (picked) => {
    if (!picked) return;
    if (picked.size > DOCUMENT_MAX_MB * 1024 * 1024) {
      toast.error(`File troppo grande (max ${DOCUMENT_MAX_MB} MB)`);
      return;
    }
    setFile(picked);
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!f.subject.trim()) { toast.error("Inserisci un oggetto"); return; }
    if (!f.contestation_date) { toast.error("Inserisci la data della contestazione"); return; }
    setSaving(true);
    try {
      // Se viene scelto un nuovo PDF, lo carica prima nella pipeline documenti
      // già esistente (stesso meccanismo di DocumentiTab) per ottenere il
      // document_id da collegare al record — senza duplicare l'upload.
      let documentId = initial?.document_id || null;
      if (file) {
        const fd = new FormData();
        fd.append("file", file);
        fd.append("name", f.subject.trim());
        fd.append("category", "contestazione_disciplinare");
        fd.append("notes", "");
        const data = await uploadEmployeeDocument(employeeId, fd);
        documentId = data.id;
      }
      const payload = {
        ...f,
        event_date: f.event_date || null,
        received_date: f.received_date || null,
        justification_deadline: f.justification_deadline || null,
        justification_date: f.justification_submitted ? (f.justification_date || null) : null,
        document_id: documentId,
      };
      if (initial) {
        await updateDisciplinaryAction(employeeId, initial.id, payload);
        toast.success("Contestazione aggiornata");
      } else {
        await createDisciplinaryAction(employeeId, payload);
        toast.success("Contestazione registrata");
      }
      onDone();
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={submit} className="bg-[#F9F9F8] border border-[#E4E4E1] rounded-md p-3 space-y-2.5 mb-3">
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1">Tipo</label>
          <select value={f.type} onChange={(e) => setF({ ...f, type: e.target.value })}
            className="w-full bg-white border border-[#E4E4E1] rounded-md px-2 py-2 text-[13px]">
            {Object.entries(CONTESTAZIONE_TYPE_LABELS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
          </select>
        </div>
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1">Data della contestazione</label>
          <input type="date" value={f.contestation_date} onChange={(e) => setF({ ...f, contestation_date: e.target.value })}
            className="w-full bg-white border border-[#E4E4E1] rounded-md px-2 py-2 text-[13px]" />
        </div>
      </div>
      <input value={f.subject} onChange={(e) => setF({ ...f, subject: e.target.value })} placeholder="Oggetto"
        className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
      <textarea value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} placeholder="Descrizione dei fatti (opzionale)" rows={3}
        className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1">Data dei fatti</label>
          <input type="date" value={f.event_date} onChange={(e) => setF({ ...f, event_date: e.target.value })}
            className="w-full bg-white border border-[#E4E4E1] rounded-md px-2 py-2 text-[13px]" />
        </div>
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1">Ricevuta il</label>
          <input type="date" value={f.received_date} onChange={(e) => setF({ ...f, received_date: e.target.value })}
            className="w-full bg-white border border-[#E4E4E1] rounded-md px-2 py-2 text-[13px]" />
        </div>
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1">Termine giustificazioni</label>
          <input type="date" value={f.justification_deadline} onChange={(e) => setF({ ...f, justification_deadline: e.target.value })}
            className="w-full bg-white border border-[#E4E4E1] rounded-md px-2 py-2 text-[13px]" />
        </div>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1">Giustificazioni presentate</label>
          <select value={f.justification_submitted ? "si" : "no"} onChange={(e) => {
            const submitted = e.target.value === "si";
            // Coerente col model_validator lato backend: se non presentate, la data va azzerata.
            setF({ ...f, justification_submitted: submitted, justification_date: submitted ? f.justification_date : "" });
          }} className="w-full bg-white border border-[#E4E4E1] rounded-md px-2 py-2 text-[13px]">
            <option value="no">No</option>
            <option value="si">Sì</option>
          </select>
        </div>
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1">Data giustificazioni</label>
          <input type="date" disabled={!f.justification_submitted} value={f.justification_date}
            onChange={(e) => setF({ ...f, justification_date: e.target.value })}
            className="w-full bg-white border border-[#E4E4E1] rounded-md px-2 py-2 text-[13px] disabled:opacity-50" />
        </div>
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1">Esito</label>
          <select value={f.outcome} onChange={(e) => setF({ ...f, outcome: e.target.value })}
            className="w-full bg-white border border-[#E4E4E1] rounded-md px-2 py-2 text-[13px]">
            {Object.entries(CONTESTAZIONE_OUTCOME_LABELS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
          </select>
        </div>
      </div>
      <input value={f.sanction} onChange={(e) => setF({ ...f, sanction: e.target.value })} placeholder="Sanzione applicata (opzionale)"
        className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
      <input value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} placeholder="Note (opzionale)"
        className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
      <div>
        <input ref={fileRef} type="file" accept="application/pdf" className="hidden" onChange={(e) => onPick(e.target.files?.[0])} />
        <button type="button" onClick={() => fileRef.current?.click()}
          className="w-full flex items-center justify-center gap-2 px-3 py-2.5 border border-dashed border-[#E4E4E1] rounded-md text-[12px] font-medium hover:border-[#B23E00]">
          <Upload className="w-4 h-4" />
          {file ? file.name : initial?.document_id ? "Sostituisci PDF allegato" : "Allega PDF (opzionale)"}
        </button>
      </div>
      <div className="flex gap-2">
        <button type="submit" disabled={saving} className="flex-1 bg-[#0A192F] text-white py-2 rounded-md text-[12px] font-medium disabled:opacity-60">
          {saving ? "Salvataggio…" : initial ? "Aggiorna" : "Registra"}
        </button>
        <button type="button" onClick={onCancel} className="px-4 py-2 border border-[#E4E4E1] rounded-md text-[12px] font-medium">
          Annulla
        </button>
      </div>
    </form>
  );
}
