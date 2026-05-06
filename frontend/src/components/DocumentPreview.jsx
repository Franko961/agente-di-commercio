import { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "./ui/dialog";
import { Download, ExternalLink, FileText, Video, FileSpreadsheet, FileImage, File as FileIcon } from "lucide-react";
import api from "../api";

const FILE_BASE = process.env.REACT_APP_BACKEND_URL;

function detectKind(doc) {
  const ct = (doc?.content_type || "").toLowerCase();
  const ext = (doc?.original_filename || doc?.name || "").split(".").pop().toLowerCase();
  if (ct.includes("pdf") || ext === "pdf") return "pdf";
  if (ct.startsWith("video/") || ["mp4", "mov", "webm", "avi", "mkv"].includes(ext)) return "video";
  if (ct.startsWith("image/") || ["png", "jpg", "jpeg", "webp", "gif"].includes(ext)) return "image";
  if (ct.startsWith("text/") || ["txt", "csv"].includes(ext)) return "text";
  return "other";
}

export default function DocumentPreview({ document: doc, open, onClose }) {
  const [blobUrl, setBlobUrl] = useState(null);
  const [textContent, setTextContent] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const kind = detectKind(doc);

  useEffect(() => {
    if (!open || !doc?.id || !doc?.storage_path) return;
    let revoked = false;
    let url = null;
    setBusy(true); setErr(""); setTextContent("");

    const token = localStorage.getItem("token");
    fetch(`${FILE_BASE}/api/documents/${doc.id}/download`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (r) => {
        if (!r.ok) throw new Error("HTTP " + r.status);
        if (kind === "text") {
          const t = await r.text();
          if (!revoked) setTextContent(t);
        } else {
          const blob = await r.blob();
          url = URL.createObjectURL(blob);
          if (!revoked) setBlobUrl(url);
        }
      })
      .catch((e) => setErr("Impossibile caricare il documento"))
      .finally(() => setBusy(false));

    return () => {
      revoked = true;
      if (url) URL.revokeObjectURL(url);
      setBlobUrl(null);
    };
  }, [open, doc?.id, doc?.storage_path, kind]);

  const triggerDownload = () => {
    if (!blobUrl && !textContent) return;
    const a = window.document.createElement("a");
    a.href = blobUrl || URL.createObjectURL(new Blob([textContent]));
    a.download = doc?.original_filename || doc?.name || "file";
    window.document.body.appendChild(a);
    a.click();
    a.remove();
  };

  if (!doc) return null;

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-4xl max-h-[92vh] p-0 gap-0 overflow-hidden">
        <DialogHeader className="px-5 py-3 border-b border-[#E4E4E1]">
          <DialogTitle className="font-cabinet text-lg flex items-center gap-2 min-w-0">
            <span className="truncate">{doc.name}</span>
          </DialogTitle>
          <div className="flex items-center justify-between gap-3 mt-1">
            <div className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA] truncate">
              {doc.original_filename}
            </div>
            <button
              data-testid="preview-download-button"
              onClick={triggerDownload}
              className="flex items-center gap-1.5 text-[11px] font-mono uppercase tracking-widest text-[#FF5A00] hover:underline shrink-0"
            >
              <Download className="w-3 h-3" /> scarica
            </button>
          </div>
        </DialogHeader>

        <div className="bg-[#0A0A0A] flex items-center justify-center min-h-[60vh] max-h-[80vh] overflow-auto">
          {busy && <div className="font-mono text-sm text-[#A1A1AA]">caricamento anteprima…</div>}
          {err && <div className="font-mono text-sm text-[#DC2626]">{err}</div>}
          {!busy && !err && blobUrl && kind === "pdf" && (
            <iframe data-testid="preview-pdf" src={blobUrl} title={doc.name}
                    className="w-full h-[80vh] bg-white" />
          )}
          {!busy && !err && blobUrl && kind === "video" && (
            <video data-testid="preview-video" src={blobUrl} controls autoPlay
                   className="max-w-full max-h-[80vh] bg-black" />
          )}
          {!busy && !err && blobUrl && kind === "image" && (
            <img data-testid="preview-image" src={blobUrl} alt={doc.name}
                 className="max-w-full max-h-[80vh] object-contain bg-white" />
          )}
          {!busy && !err && kind === "text" && textContent && (
            <pre data-testid="preview-text" className="bg-white text-[#0A0A0A] p-6 font-mono text-[12px] w-full max-h-[80vh] overflow-auto whitespace-pre-wrap">{textContent}</pre>
          )}
          {!busy && !err && kind === "other" && (
            <div className="text-center p-10">
              <FileIcon className="w-12 h-12 text-[#A1A1AA] mx-auto mb-3" />
              <div className="text-white font-medium mb-2">Anteprima non disponibile per questo tipo di file</div>
              <div className="font-mono text-[11px] text-[#A1A1AA]">{doc.content_type}</div>
              <button onClick={triggerDownload}
                      className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-[#FF5A00] hover:bg-[#E04F00] text-white rounded-md text-[13px] font-medium">
                <Download className="w-4 h-4" /> Scarica per aprire
              </button>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
