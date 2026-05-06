import { useEffect, useState, useRef } from "react";
import api from "../api";
import { Plus, FileText, Trash2, Upload, Download, FileSpreadsheet, Video, FileImage, File as FileIcon, X } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "../components/ui/dialog";
import { toast } from "sonner";
import { format, parseISO } from "date-fns";
import { it } from "date-fns/locale";

const CAT_COLORS = { contratto: "#0A192F", offerta: "#FF5A00", fattura: "#059669", listino: "#6B2C2C", video: "#7C3AED", altro: "#52525B" };
const FILE_BASE = process.env.REACT_APP_BACKEND_URL;
const MAX_MB = 50;

function formatSize(bytes) {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function fileTypeIcon(contentType, filename) {
  const ct = (contentType || "").toLowerCase();
  const ext = (filename || "").split(".").pop().toLowerCase();
  if (ct.startsWith("video/") || ["mp4", "mov", "webm", "avi", "mkv"].includes(ext)) return Video;
  if (ct.includes("spreadsheet") || ct.includes("excel") || ["xls", "xlsx", "csv"].includes(ext)) return FileSpreadsheet;
  if (ct.includes("pdf") || ext === "pdf") return FileText;
  if (ct.startsWith("image/") || ["png", "jpg", "jpeg", "webp", "gif"].includes(ext)) return FileImage;
  return FileIcon;
}

function fileTypeColor(contentType, filename) {
  const ct = (contentType || "").toLowerCase();
  const ext = (filename || "").split(".").pop().toLowerCase();
  if (ct.startsWith("video/") || ["mp4", "mov", "webm"].includes(ext)) return "#7C3AED";
  if (ct.includes("spreadsheet") || ct.includes("excel") || ["xls", "xlsx", "csv"].includes(ext)) return "#059669";
  if (ct.includes("pdf") || ext === "pdf") return "#DC2626";
  if (ct.startsWith("image/")) return "#FF5A00";
  return "#52525B";
}

export default function Documents() {
  const [docs, setDocs] = useState([]);
  const [clients, setClients] = useState([]);
  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState("all");

  const load = async () => {
    const [d, c] = await Promise.all([api.get("/documents"), api.get("/clients")]);
    setDocs(d.data); setClients(c.data);
  };
  useEffect(() => { load(); }, []);

  const remove = async (id) => {
    if (!window.confirm("Eliminare il documento?")) return;
    await api.delete(`/documents/${id}`);
    toast.success("Documento eliminato");
    load();
  };

  const download = async (doc) => {
    if (!doc.storage_path) {
      // legacy doc without file - just show notes/url
      if (doc.url) window.open(doc.url, "_blank");
      else toast.info("Questo documento non ha un file allegato");
      return;
    }
    const token = localStorage.getItem("token");
    try {
      const res = await fetch(`${FILE_BASE}/api/documents/${doc.id}/download`, {
        headers: { Authorization: `Bearer ${token}` },
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
    } catch (e) {
      toast.error("Errore download");
    }
  };

  const filtered = filter === "all" ? docs : docs.filter(d => d.category === filter);

  return (
    <div className="p-4 md:p-8">
      <div className="flex items-end justify-between border-b border-[#E4E4E1] pb-6 mb-6">
        <div>
          <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#FF5A00] mb-2">Archivio</div>
          <h1 className="font-cabinet font-black text-3xl md:text-4xl tracking-tight">Documenti</h1>
          <p className="text-[14px] text-[#52525B] mt-2 hidden md:block">Carica PDF, Excel, video e collegali ai clienti.</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <button data-testid="new-doc-button" className="flex items-center gap-2 px-4 py-2.5 bg-[#0A192F] hover:bg-[#172A45] text-white rounded-md text-[13px] font-medium">
              <Upload className="w-4 h-4 text-[#FF5A00]" /> Carica documento
            </button>
          </DialogTrigger>
          <DialogContent className="max-w-lg">
            <DialogHeader><DialogTitle className="font-cabinet">Nuovo documento</DialogTitle></DialogHeader>
            <UploadForm clients={clients} onDone={() => { load(); setOpen(false); }} />
          </DialogContent>
        </Dialog>
      </div>

      {/* Category filter */}
      <div className="flex gap-2 mb-4 overflow-x-auto">
        {["all", "contratto", "offerta", "fattura", "listino", "video", "altro"].map(c => (
          <button key={c} data-testid={`filter-cat-${c}`} onClick={() => setFilter(c)}
                  className={`px-3 py-1.5 rounded-md text-[12px] font-medium whitespace-nowrap capitalize ${filter === c ? "bg-[#0A192F] text-white" : "bg-white border border-[#E4E4E1] text-[#52525B]"}`}>
            {c === "all" ? "Tutti" : c}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {filtered.map(d => {
          const cli = clients.find(c => c.id === d.client_id);
          const Icon = fileTypeIcon(d.content_type, d.original_filename || d.name);
          const color = fileTypeColor(d.content_type, d.original_filename || d.name);
          return (
            <div key={d.id} data-testid={`doc-${d.id}`} className="bg-white border border-[#E4E4E1] rounded-md p-4 flex flex-col">
              <div className="flex items-start justify-between mb-3">
                <div className="w-10 h-10 rounded-md flex items-center justify-center" style={{ background: `${color}15` }}>
                  <Icon className="w-5 h-5" style={{ color }} />
                </div>
                <button data-testid={`delete-doc-${d.id}`} onClick={() => remove(d.id)} className="text-[#A1A1AA] hover:text-[#DC2626]"><Trash2 className="w-3.5 h-3.5" /></button>
              </div>
              <div className="font-cabinet font-bold text-[14px] leading-tight flex-1">{d.name}</div>
              {d.original_filename && <div className="font-mono text-[10px] text-[#A1A1AA] mt-1 truncate">{d.original_filename}</div>}
              <div className="flex items-center justify-between mt-2">
                <div className="font-mono text-[10px] uppercase tracking-widest" style={{ color: CAT_COLORS[d.category] || "#52525B" }}>{d.category}</div>
                {d.size && <div className="font-mono text-[10px] text-[#A1A1AA]">{formatSize(d.size)}</div>}
              </div>
              {cli && <div className="text-[12px] text-[#52525B] mt-3 pt-3 border-t border-[#E4E4E1] truncate">{cli.company_name}</div>}
              <div className="text-[10px] text-[#A1A1AA] font-mono mt-1">
                {d.created_at ? format(parseISO(d.created_at), "d MMM yyyy", { locale: it }) : ""}
              </div>
              {d.storage_path && (
                <button data-testid={`download-doc-${d.id}`} onClick={() => download(d)}
                        className="mt-3 w-full flex items-center justify-center gap-1.5 text-[11px] font-mono uppercase tracking-widest border border-[#E4E4E1] hover:border-[#0A192F] py-2 rounded">
                  <Download className="w-3 h-3" /> scarica
                </button>
              )}
            </div>
          );
        })}
        {filtered.length === 0 && (
          <div className="md:col-span-3 bg-white border border-[#E4E4E1] rounded-md p-12 text-center">
            <Upload className="w-8 h-8 text-[#A1A1AA] mx-auto mb-3" />
            <div className="text-[14px] font-medium text-[#0A0A0A]">Nessun documento</div>
            <div className="text-[12px] text-[#A1A1AA] mt-1">Carica il primo file (PDF, Excel, video, immagini fino a {MAX_MB} MB).</div>
          </div>
        )}
      </div>
    </div>
  );
}

function UploadForm({ clients, onDone }) {
  const fileInputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [name, setName] = useState("");
  const [category, setCategory] = useState("contratto");
  const [clientId, setClientId] = useState("");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [drag, setDrag] = useState(false);

  const onPick = (f) => {
    if (!f) return;
    if (f.size > MAX_MB * 1024 * 1024) {
      toast.error(`File troppo grande (max ${MAX_MB} MB)`);
      return;
    }
    setFile(f);
    if (!name) setName(f.name.replace(/\.[^.]+$/, ""));
    // Auto-detect category
    const ext = f.name.split(".").pop().toLowerCase();
    if (["mp4", "mov", "webm", "avi", "mkv"].includes(ext)) setCategory("video");
    else if (["xls", "xlsx", "csv"].includes(ext)) setCategory("listino");
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!file) { toast.error("Seleziona un file"); return; }
    if (!name.trim()) { toast.error("Inserisci un nome"); return; }
    setBusy(true);
    setProgress(0);
    const fd = new FormData();
    fd.append("file", file);
    fd.append("name", name.trim());
    fd.append("category", category);
    if (clientId) fd.append("client_id", clientId);
    fd.append("notes", notes);
    try {
      await api.post("/documents/upload", fd, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: (p) => setProgress(Math.round((p.loaded / p.total) * 100)),
      });
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
    <form onSubmit={submit} className="space-y-3">
      {/* Drop zone */}
      <div
        data-testid="upload-dropzone"
        onClick={() => fileInputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); onPick(e.dataTransfer.files[0]); }}
        className={`border-2 border-dashed rounded-md p-6 text-center cursor-pointer transition-colors ${drag ? "border-[#FF5A00] bg-[#FF5A00]/5" : "border-[#E4E4E1] hover:border-[#0A192F] bg-[#F9F9F8]"}`}
      >
        <input
          ref={fileInputRef} type="file"
          data-testid="file-input"
          accept=".pdf,.xls,.xlsx,.csv,.doc,.docx,.txt,.png,.jpg,.jpeg,.mp4,.mov,.webm,.avi,.mkv"
          onChange={(e) => onPick(e.target.files[0])}
          className="hidden"
        />
        {file ? (
          <div>
            <div className="font-cabinet font-bold text-[14px]">{file.name}</div>
            <div className="font-mono text-[11px] text-[#A1A1AA] mt-1">{formatSize(file.size)}</div>
            <button type="button" onClick={(e) => { e.stopPropagation(); setFile(null); }} className="mt-2 text-[11px] font-mono uppercase tracking-widest text-[#DC2626]">
              <X className="w-3 h-3 inline mr-1" /> rimuovi
            </button>
          </div>
        ) : (
          <div>
            <Upload className="w-7 h-7 text-[#A1A1AA] mx-auto mb-2" />
            <div className="text-[13px] font-medium">Trascina un file o clicca per selezionarlo</div>
            <div className="font-mono text-[10px] text-[#A1A1AA] mt-1 uppercase tracking-widest">PDF · Excel · Word · Video · Immagini · max {MAX_MB} MB</div>
          </div>
        )}
      </div>

      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Nome documento *</label>
        <input data-testid="doc-name-input" required value={name} onChange={(e) => setName(e.target.value)}
               className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px] focus:outline-none focus:border-[#0A192F]" />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Categoria</label>
          <select data-testid="doc-category-select" value={category} onChange={(e) => setCategory(e.target.value)}
                  className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]">
            <option value="contratto">Contratto</option>
            <option value="offerta">Offerta</option>
            <option value="fattura">Fattura</option>
            <option value="listino">Listino</option>
            <option value="video">Video</option>
            <option value="altro">Altro</option>
          </select>
        </div>
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Cliente collegato</label>
          <select data-testid="doc-client-select" value={clientId} onChange={(e) => setClientId(e.target.value)}
                  className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]">
            <option value="">— nessuno —</option>
            {clients.map(c => <option key={c.id} value={c.id}>{c.company_name}</option>)}
          </select>
        </div>
      </div>

      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Note</label>
        <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2}
                  className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
      </div>

      {busy && progress < 100 && (
        <div className="bg-[#F3F3F1] rounded-full h-1.5 overflow-hidden">
          <div className="h-full bg-[#FF5A00] transition-all" style={{ width: `${progress}%` }} />
        </div>
      )}

      <button data-testid="save-doc-button" type="submit" disabled={busy || !file}
              className="w-full bg-[#0A192F] hover:bg-[#172A45] text-white py-2.5 rounded-md text-[13px] font-medium disabled:opacity-50 flex items-center justify-center gap-2">
        <Upload className="w-4 h-4 text-[#FF5A00]" />
        {busy ? `Caricamento ${progress}%…` : "Carica documento"}
      </button>
    </form>
  );
}
