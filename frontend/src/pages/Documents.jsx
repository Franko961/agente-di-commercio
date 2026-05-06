import { useEffect, useState, useRef } from "react";
import api from "../api";
import { Plus, FileText, Trash2, Upload, Download, FileSpreadsheet, Video, FileImage, File as FileIcon, X, Eye, Tag, Loader2, Sparkles } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from "../components/ui/dialog";
import { toast } from "sonner";
import { format, parseISO } from "date-fns";
import { it } from "date-fns/locale";
import DocumentPreview from "../components/DocumentPreview";
import { compressVideo, formatBytes } from "../utils/videoCompress";

const CAT_COLORS = { contratto: "#0A192F", offerta: "#FF5A00", fattura: "#059669", listino: "#6B2C2C", video: "#7C3AED", altro: "#52525B" };
const FILE_BASE = process.env.REACT_APP_BACKEND_URL;
const MAX_MB = 50;
const VIDEO_COMPRESS_THRESHOLD = 8 * 1024 * 1024; // 8 MB

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
  const [tagFilter, setTagFilter] = useState("");
  const [previewDoc, setPreviewDoc] = useState(null);

  const load = async () => {
    const [d, c] = await Promise.all([api.get("/documents"), api.get("/clients")]);
    setDocs(d.data); setClients(c.data);
  };
  useEffect(() => { load(); }, []);

  const remove = async (id) => {
    if (!window.confirm("Eliminare il documento?")) return;
    setDocs(prev => prev.filter(d => d.id !== id));
    try {
      await api.delete(`/documents/${id}`);
      toast.success("Documento eliminato");
    } catch (e) {
      toast.error("Errore eliminazione");
      load();
    }
  };

  const download = async (doc) => {
    if (!doc.storage_path) {
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

  // Compute global tag set for filter chips
  const allTags = Array.from(new Set(docs.flatMap(d => d.tags || []))).sort();

  let filtered = filter === "all" ? docs : docs.filter(d => d.category === filter);
  if (tagFilter) filtered = filtered.filter(d => (d.tags || []).includes(tagFilter));

  return (
    <div className="p-4 md:p-8">
      <div className="flex items-end justify-between border-b border-[#E4E4E1] pb-6 mb-6">
        <div>
          <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#FF5A00] mb-2">Archivio</div>
          <h1 className="font-cabinet font-black text-3xl md:text-4xl tracking-tight">Documenti</h1>
          <p className="text-[14px] text-[#52525B] mt-2 hidden md:block">PDF, Excel, video con anteprima inline e tag personalizzati.</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <button data-testid="new-doc-button" className="flex items-center gap-2 px-4 py-2.5 bg-[#0A192F] hover:bg-[#172A45] text-white rounded-md text-[13px] font-medium">
              <Upload className="w-4 h-4 text-[#FF5A00]" /> Carica documento
            </button>
          </DialogTrigger>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle className="font-cabinet">Nuovo documento</DialogTitle>
              <DialogDescription className="text-[12px] text-[#A1A1AA]">PDF · Excel · Word · Video · Immagini fino a {MAX_MB} MB.</DialogDescription>
            </DialogHeader>
            <UploadForm
              clients={clients}
              existingTags={allTags}
              onDone={(newDoc) => {
                if (newDoc) setDocs(prev => [newDoc, ...prev]);
                setOpen(false);
              }}
            />
          </DialogContent>
        </Dialog>
      </div>

      {/* Category filter */}
      <div className="flex gap-2 mb-3 overflow-x-auto">
        {["all", "contratto", "offerta", "fattura", "listino", "video", "altro"].map(c => (
          <button key={c} data-testid={`filter-cat-${c}`} onClick={() => setFilter(c)}
                  className={`px-3 py-1.5 rounded-md text-[12px] font-medium whitespace-nowrap capitalize ${filter === c ? "bg-[#0A192F] text-white" : "bg-white border border-[#E4E4E1] text-[#52525B]"}`}>
            {c === "all" ? "Tutti" : c}
          </button>
        ))}
      </div>

      {/* Tag filter chips */}
      {allTags.length > 0 && (
        <div className="flex items-center gap-2 mb-4 flex-wrap">
          <Tag className="w-3 h-3 text-[#A1A1AA]" />
          <button onClick={() => setTagFilter("")} data-testid="tag-filter-all"
                  className={`px-2 py-1 rounded text-[11px] font-mono uppercase tracking-widest ${tagFilter === "" ? "bg-[#FF5A00] text-white" : "bg-white border border-[#E4E4E1] text-[#52525B]"}`}>
            tutti i tag
          </button>
          {allTags.map(t => (
            <button key={t} onClick={() => setTagFilter(tagFilter === t ? "" : t)}
                    data-testid={`tag-filter-${t}`}
                    className={`px-2 py-1 rounded text-[11px] font-mono lowercase ${tagFilter === t ? "bg-[#FF5A00] text-white" : "bg-white border border-[#E4E4E1] text-[#52525B] hover:border-[#FF5A00]"}`}>
              #{t}
            </button>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {filtered.map(d => {
          const cli = clients.find(c => c.id === d.client_id);
          const Icon = fileTypeIcon(d.content_type, d.original_filename || d.name);
          const color = fileTypeColor(d.content_type, d.original_filename || d.name);
          return (
            <div key={d.id} data-testid={`doc-${d.id}`} className="bg-white border border-[#E4E4E1] rounded-md p-4 flex flex-col">
              <div className="flex items-start justify-between mb-3">
                <button data-testid={`preview-doc-${d.id}`} onClick={() => d.storage_path ? setPreviewDoc(d) : null}
                        className="w-10 h-10 rounded-md flex items-center justify-center transition-transform hover:scale-105"
                        style={{ background: `${color}15` }}>
                  <Icon className="w-5 h-5" style={{ color }} />
                </button>
                <button data-testid={`delete-doc-${d.id}`} onClick={() => remove(d.id)} className="text-[#A1A1AA] hover:text-[#DC2626]"><Trash2 className="w-3.5 h-3.5" /></button>
              </div>
              <div className="font-cabinet font-bold text-[14px] leading-tight flex-1">{d.name}</div>
              {d.original_filename && <div className="font-mono text-[10px] text-[#A1A1AA] mt-1 truncate">{d.original_filename}</div>}
              <div className="flex items-center justify-between mt-2">
                <div className="font-mono text-[10px] uppercase tracking-widest" style={{ color: CAT_COLORS[d.category] || "#52525B" }}>{d.category}</div>
                {d.size && <div className="font-mono text-[10px] text-[#A1A1AA]">{formatBytes(d.size)}</div>}
              </div>
              {d.tags?.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {d.tags.map(t => (
                    <span key={t} className="bg-[#F3F3F1] text-[#52525B] text-[10px] font-mono lowercase px-1.5 py-0.5 rounded">#{t}</span>
                  ))}
                </div>
              )}
              {cli && <div className="text-[12px] text-[#52525B] mt-3 pt-3 border-t border-[#E4E4E1] truncate">{cli.company_name}</div>}
              <div className="text-[10px] text-[#A1A1AA] font-mono mt-1">
                {d.created_at ? format(parseISO(d.created_at), "d MMM yyyy", { locale: it }) : ""}
              </div>
              <div className="grid grid-cols-2 gap-1 mt-3">
                {d.storage_path && (
                  <button data-testid={`open-doc-${d.id}`} onClick={() => setPreviewDoc(d)}
                          className="flex items-center justify-center gap-1.5 text-[11px] font-mono uppercase tracking-widest border border-[#E4E4E1] hover:border-[#0A192F] py-2 rounded">
                    <Eye className="w-3 h-3" /> apri
                  </button>
                )}
                {d.storage_path && (
                  <button data-testid={`download-doc-${d.id}`} onClick={() => download(d)}
                          className="flex items-center justify-center gap-1.5 text-[11px] font-mono uppercase tracking-widest border border-[#E4E4E1] hover:border-[#0A192F] py-2 rounded">
                    <Download className="w-3 h-3" /> scarica
                  </button>
                )}
              </div>
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

      <DocumentPreview document={previewDoc} open={!!previewDoc} onClose={() => setPreviewDoc(null)} />
    </div>
  );
}

function UploadForm({ clients, existingTags, onDone }) {
  const fileInputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [originalSize, setOriginalSize] = useState(0);
  const [name, setName] = useState("");
  const [category, setCategory] = useState("contratto");
  const [clientId, setClientId] = useState("");
  const [notes, setNotes] = useState("");
  const [tags, setTags] = useState([]);
  const [tagInput, setTagInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [phase, setPhase] = useState(""); // "compressing" | "uploading"
  const [drag, setDrag] = useState(false);

  const onPick = (f) => {
    if (!f) return;
    if (f.size > MAX_MB * 1024 * 1024) {
      toast.error(`File troppo grande (max ${MAX_MB} MB)`);
      return;
    }
    setFile(f);
    setOriginalSize(f.size);
    if (!name) setName(f.name.replace(/\.[^.]+$/, ""));
    const ext = f.name.split(".").pop().toLowerCase();
    if (["mp4", "mov", "webm", "avi", "mkv"].includes(ext)) setCategory("video");
    else if (["xls", "xlsx", "csv"].includes(ext)) setCategory("listino");
  };

  const addTag = (raw) => {
    const t = raw.trim().toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9\-_àèéìòù]/g, "");
    if (!t || tags.includes(t)) return;
    setTags([...tags, t]);
    setTagInput("");
  };

  const onTagKey = (e) => {
    if (["Enter", ",", "Tab"].includes(e.key)) {
      e.preventDefault();
      if (tagInput) addTag(tagInput);
    } else if (e.key === "Backspace" && !tagInput && tags.length) {
      setTags(tags.slice(0, -1));
    }
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!file) { toast.error("Seleziona un file"); return; }
    if (!name.trim()) { toast.error("Inserisci un nome"); return; }

    setBusy(true);
    setProgress(0);

    let toUpload = file;
    // Compress video if large enough to warrant it
    if (file.type.startsWith("video/") && file.size > VIDEO_COMPRESS_THRESHOLD) {
      try {
        setPhase("compressing");
        toUpload = await compressVideo(file, (p) => setProgress(p));
        if (toUpload !== file) {
          const saved = file.size - toUpload.size;
          if (saved > 0) toast.success(`Video compresso: -${formatBytes(saved)} (${Math.round((saved / file.size) * 100)}%)`);
        }
      } catch (err) {
        toast.error("Compressione fallita, carico l'originale");
        toUpload = file;
      }
      setProgress(0);
    }

    setPhase("uploading");
    const fd = new FormData();
    fd.append("file", toUpload);
    fd.append("name", name.trim());
    fd.append("category", category);
    if (clientId) fd.append("client_id", clientId);
    fd.append("notes", notes);
    if (tags.length) fd.append("tags", tags.join(","));

    try {
      const { data } = await api.post("/documents/upload", fd, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: (p) => setProgress(p.total ? Math.round((p.loaded / p.total) * 100) : 0),
      });
      toast.success("Documento caricato");
      onDone(data);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Errore caricamento");
    } finally {
      setBusy(false);
      setPhase("");
    }
  };

  const willCompress = file && file.type.startsWith("video/") && file.size > VIDEO_COMPRESS_THRESHOLD;

  return (
    <form onSubmit={submit} className="space-y-3">
      {/* Drop zone */}
      <div
        data-testid="upload-dropzone"
        onClick={() => !busy && fileInputRef.current?.click()}
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
            <div className="font-mono text-[11px] text-[#A1A1AA] mt-1">{formatBytes(file.size)}</div>
            {willCompress && (
              <div className="mt-2 inline-flex items-center gap-1.5 bg-[#7C3AED]/10 text-[#7C3AED] text-[10px] font-mono uppercase tracking-widest px-2 py-1 rounded">
                <Sparkles className="w-3 h-3" /> sarà compresso in webm
              </div>
            )}
            <div className="mt-2">
              <button type="button" onClick={(e) => { e.stopPropagation(); setFile(null); }} className="text-[11px] font-mono uppercase tracking-widest text-[#DC2626]">
                <X className="w-3 h-3 inline mr-1" /> rimuovi
              </button>
            </div>
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

      {/* Tags input */}
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Tag personalizzati</label>
        <div className="bg-white border border-[#E4E4E1] rounded-md px-2 py-1.5 flex flex-wrap items-center gap-1 focus-within:border-[#0A192F] transition-colors">
          {tags.map(t => (
            <span key={t} data-testid={`tag-chip-${t}`} className="flex items-center gap-1 bg-[#FF5A00]/10 text-[#FF5A00] text-[11px] font-mono lowercase px-2 py-0.5 rounded">
              #{t}
              <button type="button" onClick={() => setTags(tags.filter(x => x !== t))} className="hover:text-[#DC2626]">
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}
          <input
            data-testid="tag-input"
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            onKeyDown={onTagKey}
            onBlur={() => tagInput && addTag(tagInput)}
            placeholder={tags.length ? "" : "es. urgente, prodotto-2026 (Invio)"}
            className="flex-1 min-w-[120px] outline-none text-[13px] py-1"
          />
        </div>
        {existingTags?.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            <span className="font-mono text-[10px] text-[#A1A1AA] uppercase tracking-widest">suggeriti:</span>
            {existingTags.filter(t => !tags.includes(t)).slice(0, 8).map(t => (
              <button key={t} type="button" onClick={() => addTag(t)} className="text-[10px] font-mono lowercase text-[#52525B] hover:text-[#FF5A00]">#{t}</button>
            ))}
          </div>
        )}
      </div>

      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Note</label>
        <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2}
                  className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
      </div>

      {busy && (
        <div className="space-y-1">
          <div className="flex items-center justify-between text-[11px] font-mono uppercase tracking-widest text-[#52525B]">
            <span className="flex items-center gap-1.5">
              <Loader2 className="w-3 h-3 animate-spin" />
              {phase === "compressing" ? "compressione video" : "caricamento"}
            </span>
            <span>{progress}%</span>
          </div>
          <div className="bg-[#F3F3F1] rounded-full h-1.5 overflow-hidden">
            <div className="h-full bg-[#FF5A00] transition-all" style={{ width: `${progress}%` }} />
          </div>
        </div>
      )}

      <button data-testid="save-doc-button" type="submit" disabled={busy || !file}
              className="w-full bg-[#0A192F] hover:bg-[#172A45] text-white py-2.5 rounded-md text-[13px] font-medium disabled:opacity-50 flex items-center justify-center gap-2">
        <Upload className="w-4 h-4 text-[#FF5A00]" />
        {busy ? `${phase === "compressing" ? "Compressione" : "Caricamento"} ${progress}%…` : "Carica documento"}
      </button>
    </form>
  );
}
