import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import api from "../api";
import { ArrowLeft, MapPin, Phone, Mail, Building, Trash2, Edit, Calendar, FileText, Folder, Coins, MessageCircle, Send, Eye, Download } from "lucide-react";
import { format, parseISO } from "date-fns";
import { it } from "date-fns/locale";
import { toast } from "sonner";
import { whatsappLink } from "../utils/export";
import DocumentPreview from "../components/DocumentPreview";

const fmt = (n) => new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(n || 0);

const TABS = [
  { id: "info", label: "Informazioni", icon: Building },
  { id: "offerte", label: "Offerte", icon: FileText },
  { id: "agenda", label: "Visite", icon: Calendar },
  { id: "documenti", label: "Documenti", icon: Folder },
  { id: "provvigioni", label: "Provvigioni", icon: Coins },
];

export default function ClientDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [tab, setTab] = useState("info");
  const [data, setData] = useState(null);
  const [previewDoc, setPreviewDoc] = useState(null);

  const load = () => api.get(`/clients/${id}`).then(({ data }) => setData(data));
  useEffect(() => { load(); }, [id]);

  const remove = async () => {
    if (!window.confirm("Eliminare il cliente?")) return;
    await api.delete(`/clients/${id}`);
    toast.success("Cliente eliminato");
    navigate("/clienti");
  };

  if (!data) return <div className="p-8 font-mono text-sm text-[#A1A1AA]">caricamento…</div>;
  const c = data.client;

  return (
    <div className="p-4 md:p-8 space-y-6">
      <Link to="/clienti" className="inline-flex items-center gap-2 text-[12px] font-mono uppercase tracking-widest text-[#52525B]">
        <ArrowLeft className="w-3.5 h-3.5" /> Torna ai clienti
      </Link>

      <div className="bg-white border border-[#E4E4E1] rounded-md p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="font-mono text-[10px] uppercase tracking-widest text-[#FF5A00] mb-2">{c.zone || "Italia"} · {c.sector || "Settore"}</div>
            <h1 className="font-cabinet font-black text-3xl tracking-tight">{c.company_name}</h1>
            <div className="text-[14px] text-[#52525B] mt-1">{c.contact_name}</div>
            <div className="flex flex-wrap gap-4 mt-4 text-[13px] text-[#52525B]">
              {c.email && <span className="flex items-center gap-1.5"><Mail className="w-3.5 h-3.5" />{c.email}</span>}
              {c.phone && <span className="flex items-center gap-1.5"><Phone className="w-3.5 h-3.5" />{c.phone}</span>}
              {c.city && <span className="flex items-center gap-1.5"><MapPin className="w-3.5 h-3.5" />{c.address}, {c.city} ({c.province})</span>}
            </div>
            <div className="flex flex-wrap gap-2 mt-4">
              {c.phone && (
                <a
                  data-testid="whatsapp-button"
                  href={whatsappLink(c.phone, `Buongiorno ${c.contact_name || ""}, sono il vostro agente di commercio.`)}
                  target="_blank" rel="noopener noreferrer"
                  className="flex items-center gap-2 px-3 py-2 bg-[#25D366] hover:opacity-90 text-white rounded-md text-[12px] font-medium"
                >
                  <MessageCircle className="w-3.5 h-3.5" /> WhatsApp
                </a>
              )}
              {c.phone && (
                <a
                  data-testid="call-button"
                  href={`tel:${c.phone.replace(/\s/g, "")}`}
                  className="flex items-center gap-2 px-3 py-2 border border-[#E4E4E1] hover:border-[#0A192F] rounded-md text-[12px] font-medium"
                >
                  <Phone className="w-3.5 h-3.5" /> Chiama
                </a>
              )}
              {c.email && (
                <a
                  data-testid="email-button"
                  href={`mailto:${c.email}?subject=Saluti%20da%20parte%20del%20vostro%20agente`}
                  className="flex items-center gap-2 px-3 py-2 border border-[#E4E4E1] hover:border-[#0A192F] rounded-md text-[12px] font-medium"
                >
                  <Send className="w-3.5 h-3.5" /> Email
                </a>
              )}
            </div>
          </div>
          <button data-testid="delete-client-button" onClick={remove} className="text-[#A1A1AA] hover:text-[#DC2626] p-2"><Trash2 className="w-4 h-4" /></button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-[#E4E4E1] overflow-x-auto">
        {TABS.map(({ id: t, label, icon: Icon }) => (
          <button key={t} onClick={() => setTab(t)} data-testid={`tab-${t}`}
                  className={`flex items-center gap-2 px-4 py-3 text-[13px] font-medium whitespace-nowrap border-b-2 transition-colors ${tab === t ? "border-[#FF5A00] text-[#0A0A0A]" : "border-transparent text-[#52525B]"}`}>
            <Icon className="w-3.5 h-3.5" /> {label}
          </button>
        ))}
      </div>

      <div>
        {tab === "info" && (
          <div className="grid md:grid-cols-2 gap-4">
            <InfoCard label="P.IVA" value={c.vat_number || "—"} />
            <InfoCard label="Potenziale" value={c.potential} />
            <InfoCard label="Settore" value={c.sector || "—"} />
            <InfoCard label="Zona" value={c.zone || "—"} />
            {c.lat && c.lng && <InfoCard label="Coordinate" value={`${c.lat.toFixed(4)}, ${c.lng.toFixed(4)}`} />}
            <div className="md:col-span-2 bg-white border border-[#E4E4E1] rounded-md p-5">
              <div className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA] mb-2">Note</div>
              <div className="text-[14px] text-[#0A0A0A] whitespace-pre-wrap">{c.notes || "Nessuna nota."}</div>
            </div>
          </div>
        )}

        {tab === "offerte" && (
          <div className="space-y-2">
            {data.offers.length === 0 && <Empty>Nessuna offerta per questo cliente.</Empty>}
            {data.offers.map((o) => (
              <div key={o.id} className="bg-white border border-[#E4E4E1] rounded-md p-4 flex items-center justify-between">
                <div>
                  <div className="font-medium text-[14px]">{o.title}</div>
                  <div className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA] mt-1">{format(parseISO(o.created_at), "dd MMM yyyy", { locale: it })}</div>
                </div>
                <div className="text-right">
                  <div className="font-cabinet font-bold text-lg">{fmt(o.total)}</div>
                  <div className="font-mono text-[10px] uppercase tracking-widest text-[#FF5A00]">{o.status}</div>
                </div>
              </div>
            ))}
          </div>
        )}

        {tab === "agenda" && (
          <div className="space-y-2">
            {data.appointments.length === 0 && <Empty>Nessuna visita registrata.</Empty>}
            {data.appointments.map((a) => (
              <div key={a.id} className="bg-white border border-[#E4E4E1] rounded-md p-4 flex items-center gap-4">
                <div className="w-14 text-center">
                  <div className="font-cabinet font-black text-xl">{format(parseISO(a.start), "d")}</div>
                  <div className="font-mono text-[10px] uppercase text-[#A1A1AA]">{format(parseISO(a.start), "MMM yy", { locale: it })}</div>
                </div>
                <div className="flex-1">
                  <div className="font-medium text-[14px]">{a.title}</div>
                  <div className="text-[12px] text-[#52525B]">{format(parseISO(a.start), "HH:mm")} · {a.location}</div>
                </div>
                <span className="font-mono text-[10px] uppercase tracking-widest text-[#FF5A00]">{a.status}</span>
              </div>
            ))}
          </div>
        )}

        {tab === "documenti" && (
          <div className="space-y-2">
            {data.documents.length === 0 && <Empty>Nessun documento archiviato.</Empty>}
            {data.documents.map((d) => {
              const ct = (d.content_type || "").toLowerCase();
              const ext = (d.original_filename || d.name || "").split(".").pop().toLowerCase();
              const isVideo = ct.startsWith("video/") || ["mp4", "mov", "webm"].includes(ext);
              const isPdf = ct.includes("pdf") || ext === "pdf";
              const isImg = ct.startsWith("image/");
              const color = isVideo ? "#7C3AED" : isPdf ? "#DC2626" : isImg ? "#FF5A00" : "#52525B";
              return (
                <div key={d.id} className="bg-white border border-[#E4E4E1] rounded-md p-4 flex items-center justify-between gap-3">
                  <button
                    onClick={() => d.storage_path && setPreviewDoc(d)}
                    data-testid={`client-doc-${d.id}`}
                    className="flex items-center gap-3 flex-1 min-w-0 text-left"
                  >
                    <div className="w-9 h-9 rounded-md flex items-center justify-center shrink-0" style={{ background: `${color}15` }}>
                      <Folder className="w-4 h-4" style={{ color }} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="font-medium text-[14px] truncate">{d.name}</div>
                      <div className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA]">{d.category}{d.size ? ` · ${(d.size / 1024 / 1024).toFixed(1)} MB` : ""}</div>
                      {d.tags?.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-1">
                          {d.tags.map(t => <span key={t} className="bg-[#F3F3F1] text-[#52525B] text-[10px] font-mono lowercase px-1.5 py-0.5 rounded">#{t}</span>)}
                        </div>
                      )}
                    </div>
                  </button>
                  {d.storage_path && (
                    <button onClick={() => setPreviewDoc(d)} className="flex items-center gap-1 text-[11px] font-mono uppercase tracking-widest text-[#FF5A00] shrink-0">
                      <Eye className="w-3 h-3" /> apri
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {tab === "provvigioni" && (
          <div className="space-y-2">
            {data.commissions.length === 0 && <Empty>Nessuna provvigione registrata.</Empty>}
            {data.commissions.map((cm) => (
              <div key={cm.id} className="bg-white border border-[#E4E4E1] rounded-md p-4 flex items-center justify-between">
                <div>
                  <div className="font-medium text-[14px]">Periodo {cm.period}</div>
                  <div className="text-[12px] text-[#52525B]">Aliquota {cm.rate}%</div>
                </div>
                <div className="text-right">
                  <div className="font-cabinet font-bold text-lg">{fmt(cm.amount)}</div>
                  <div className="font-mono text-[10px] uppercase tracking-widest" style={{ color: cm.status === "incassato" ? "#059669" : "#FF5A00" }}>{cm.status}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <DocumentPreview document={previewDoc} open={!!previewDoc} onClose={() => setPreviewDoc(null)} />
    </div>
  );
}

function InfoCard({ label, value }) {
  return (
    <div className="bg-white border border-[#E4E4E1] rounded-md p-4">
      <div className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA] mb-1">{label}</div>
      <div className="text-[14px] font-medium">{value}</div>
    </div>
  );
}

function Empty({ children }) {
  return <div className="bg-white border border-[#E4E4E1] rounded-md p-8 text-center text-[#A1A1AA] text-[13px]">{children}</div>;
}
