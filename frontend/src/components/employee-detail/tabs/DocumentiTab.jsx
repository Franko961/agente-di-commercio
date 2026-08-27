import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { FileText, Upload, Download, Trash2 } from "lucide-react";
import api from "../../../api";
import { FILE_BASE, DOCUMENT_MAX_MB } from "../constants";

const DOCUMENT_CATEGORY_LABELS = { contratto: "Contratto", documento_identita: "Documento d'identità", patente: "Patente", contestazione_disciplinare: "Contestazione disciplinare", altro: "Altro" };

export default function DocumentiTab({ employeeId }) {
  const [docs, setDocs] = useState(null);
  const [showUpload, setShowUpload] = useState(false);

  const load = async () => {
    const { data } = await api.get(`/employees/${employeeId}/documents`);
    setDocs(data);
  };
  useEffect(() => { load(); }, [employeeId]); // eslint-disable-line react-hooks/exhaustive-deps

  const download = async (doc) => {
    try {
      const res = await fetch(`${FILE_BASE}/api/employees/${employeeId}/documents/${doc.id}/download`, {
        credentials: "include",
      });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = doc.original_filename || doc.name;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch {
      toast.error("Errore download");
    }
  };

  const remove = async (doc) => {
    if (!window.confirm(`Eliminare "${doc.name}"?`)) return;
    try {
      await api.delete(`/employees/${employeeId}/documents/${doc.id}`);
      toast.success("Documento eliminato");
      load();
    } catch {
      toast.error("Errore eliminazione");
    }
  };

  return (
    <div>
      <div className="flex justify-end mb-3">
        <button onClick={() => setShowUpload((v) => !v)}
          className="flex items-center gap-1.5 px-3 py-2 bg-[#0A192F] text-white rounded-md text-[12px] font-medium">
          <Upload className="w-3.5 h-3.5" /> Carica documento
        </button>
      </div>
      {showUpload && (
        <EmployeeDocumentUploadForm employeeId={employeeId} onDone={() => { setShowUpload(false); load(); }} />
      )}
      <div className="space-y-2 mt-3">
        {(docs || []).map((d) => (
          <div key={d.id} className="bg-white border border-[#E4E4E1] rounded-md p-3 flex items-center justify-between gap-2 flex-wrap text-[13px]">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-[#6B6B72] shrink-0" />
                <span className="font-medium truncate">{d.name}</span>
                <span className="font-mono text-[10px] uppercase tracking-widest text-[#6B6B72] shrink-0">{DOCUMENT_CATEGORY_LABELS[d.category] || d.category}</span>
              </div>
              <div className="text-[11px] text-[#6B6B72] mt-0.5">{new Date(d.created_at).toLocaleDateString("it-IT")}{d.notes ? ` · ${d.notes}` : ""}</div>
            </div>
            <div className="flex gap-1 shrink-0">
              <button onClick={() => download(d)} title="Scarica" aria-label="Scarica documento"
                className="p-1.5 text-[#6B6B72] hover:text-[#0A192F] hover:bg-[#F3F3F1] rounded"><Download className="w-4 h-4" /></button>
              <button onClick={() => remove(d)} title="Elimina" aria-label="Elimina documento"
                className="p-1.5 text-[#6B6B72] hover:text-red-500 hover:bg-red-50 rounded"><Trash2 className="w-4 h-4" /></button>
            </div>
          </div>
        ))}
        {docs && docs.length === 0 && !showUpload && (
          <div className="bg-white border border-[#E4E4E1] rounded-md p-6 text-center text-[#6B6B72] text-[13px]">Nessun documento caricato.</div>
        )}
      </div>
    </div>
  );
}

function EmployeeDocumentUploadForm({ employeeId, onDone }) {
  const fileRef = useRef(null);
  const [file, setFile] = useState(null);
  const [name, setName] = useState("");
  const [category, setCategory] = useState("altro");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);

  const onPick = (f) => {
    if (!f) return;
    if (f.size > DOCUMENT_MAX_MB * 1024 * 1024) {
      toast.error(`File troppo grande (max ${DOCUMENT_MAX_MB} MB)`);
      return;
    }
    setFile(f);
    if (!name) setName(f.name.replace(/\.[^.]+$/, ""));
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!file) { toast.error("Seleziona un file"); return; }
    setBusy(true);
    const fd = new FormData();
    fd.append("file", file);
    fd.append("name", name.trim());
    fd.append("category", category);
    fd.append("notes", notes);
    try {
      await api.post(`/employees/${employeeId}/documents/upload`, fd);
      toast.success("Documento caricato");
      onDone();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Errore caricamento");
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="bg-[#F9F9F8] border border-[#E4E4E1] rounded-md p-3 space-y-2.5 mb-3">
      <input ref={fileRef} type="file" className="hidden" onChange={(e) => onPick(e.target.files?.[0])} />
      <button type="button" onClick={() => fileRef.current?.click()}
        className="w-full flex items-center justify-center gap-2 px-3 py-2.5 border border-dashed border-[#E4E4E1] rounded-md text-[12px] font-medium hover:border-[#B23E00]">
        <Upload className="w-4 h-4" /> {file ? file.name : "Scegli file (PDF, immagine, Word, Excel)"}
      </button>
      <div className="grid grid-cols-2 gap-2">
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Nome documento"
          className="bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
        <select value={category} onChange={(e) => setCategory(e.target.value)}
          className="bg-white border border-[#E4E4E1] rounded-md px-2 py-2 text-[13px]">
          {Object.entries(DOCUMENT_CATEGORY_LABELS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
        </select>
      </div>
      <input value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Note (opzionale)"
        className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
      <button type="submit" disabled={busy} className="w-full bg-[#0A192F] text-white py-2 rounded-md text-[12px] font-medium disabled:opacity-60">
        {busy ? "Caricamento…" : "Carica"}
      </button>
    </form>
  );
}
