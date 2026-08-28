import { useRef, useState } from "react";
import { Plus, Trash2, Pencil, FileSignature, Eraser } from "lucide-react";
import SignatureCanvas from "react-signature-canvas";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "../ui/dialog";
import { CARGO_STATUS_LABELS, CARGO_STATUS_COLORS } from "./constants";

export default function CaricoTab({
  loads, activeVehicles, clients, orders,
  loadOpen, setLoadOpen, loadEditTarget, setLoadEditTarget, signTarget, setSignTarget,
  saveLoad, deleteLoad, signLoad, emptyLoad,
}) {
  return (
    <div>
      <div className="flex justify-end mb-4">
        <Dialog open={loadOpen} onOpenChange={setLoadOpen}>
          <DialogTrigger asChild>
            <button className="flex items-center gap-2 px-4 py-2.5 bg-[#0A192F] text-white rounded-md text-[13px] font-medium">
              <Plus className="w-4 h-4" /> Nuovo carico
            </button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>Nuovo carico</DialogTitle></DialogHeader>
            <LoadForm initial={emptyLoad} vehicles={activeVehicles} clients={clients} orders={orders} onSave={saveLoad} />
          </DialogContent>
        </Dialog>
      </div>
      <Dialog open={!!loadEditTarget} onOpenChange={(v) => !v && setLoadEditTarget(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle>Modifica carico</DialogTitle></DialogHeader>
          {loadEditTarget && <LoadForm initial={loadEditTarget} vehicles={activeVehicles} clients={clients} orders={orders} onSave={saveLoad} submitLabel="Aggiorna" />}
        </DialogContent>
      </Dialog>
      <Dialog open={!!signTarget} onOpenChange={(v) => !v && setSignTarget(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle>Firma consegna</DialogTitle></DialogHeader>
          {signTarget && <CargoSignatureForm load={signTarget} onSign={signLoad} onClose={() => setSignTarget(null)} />}
        </DialogContent>
      </Dialog>

      <div className="space-y-2">
        {loads.map((l) => (
          <div key={l.id} className="bg-white border border-[#E4E4E1] rounded-md p-4 flex items-center justify-between gap-3 flex-wrap">
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-cabinet font-bold text-[14px]">{l.vehicle_plate}</span>
                <span className="text-[12px] text-[#52525B]">{l.date}</span>
                <span className="font-mono text-[10px] uppercase tracking-widest px-1.5 py-0.5 rounded-full"
                  style={{ background: `${CARGO_STATUS_COLORS[l.status]}1A`, color: CARGO_STATUS_COLORS[l.status] }}>
                  {CARGO_STATUS_LABELS[l.status]}
                </span>
              </div>
              <div className="text-[13px] mt-1">{l.description}</div>
              {l.destination && <div className="text-[12px] text-[#52525B] mt-0.5">Destinazione: {l.destination}</div>}
              {(l.quantity || l.colli || l.peso) && (
                <div className="text-[12px] text-[#52525B] mt-0.5">
                  {[
                    l.quantity ? `Quantità: ${l.quantity}` : null,
                    l.colli ? `Colli: ${l.colli}` : null,
                    l.peso ? `Peso: ${l.peso} kg` : null,
                  ].filter(Boolean).join(" · ")}
                </div>
              )}
              {l.notes && <div className="text-[12px] text-[#6B6B72] mt-0.5 italic">{l.notes}</div>}
              {l.signed_at && (
                <div className="text-[12px] text-[#059669] mt-1">Firmato da {l.signer_name} il {new Date(l.signed_at).toLocaleString("it-IT")}</div>
              )}
            </div>
            <div className="flex gap-1">
              {!l.signed_at && (
                <button onClick={() => setSignTarget(l)} title="Firma consegna" aria-label="Firma consegna"
                  className="p-1.5 text-[#6B6B72] hover:text-[#059669] hover:bg-green-50 rounded"><FileSignature className="w-4 h-4" /></button>
              )}
              <button onClick={() => setLoadEditTarget(l)} title="Modifica" aria-label="Modifica carico"
                className="p-1.5 text-[#6B6B72] hover:text-[#0A192F] hover:bg-[#F3F3F1] rounded"><Pencil className="w-4 h-4" /></button>
              <button onClick={() => deleteLoad(l.id)} title="Elimina" aria-label="Elimina carico"
                className="p-1.5 text-[#6B6B72] hover:text-red-500 hover:bg-red-50 rounded"><Trash2 className="w-4 h-4" /></button>
            </div>
          </div>
        ))}
        {loads.length === 0 && (
          <div className="bg-white border border-[#E4E4E1] rounded-md p-8 text-center text-[#6B6B72] text-[13px]">Nessun carico ancora registrato.</div>
        )}
      </div>
    </div>
  );
}

function LoadForm({ initial, vehicles, clients, orders, onSave, submitLabel = "Salva" }) {
  const [f, setF] = useState({
    vehicle_id: initial.vehicle_id || (vehicles[0]?.id || ""), date: initial.date || "",
    description: initial.description || "", destination: initial.destination || "", notes: initial.notes || "",
    client_id: initial.client_id || "", order_id: initial.order_id || "",
    quantity: initial.quantity ?? "", colli: initial.colli ?? "", peso: initial.peso ?? "",
    status: initial.status || "programmato",
  });
  return (
    <form onSubmit={async (e) => { e.preventDefault(); await onSave(f); }} className="space-y-3">
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Mezzo *</label>
        <select required value={f.vehicle_id} onChange={(e) => setF({ ...f, vehicle_id: e.target.value })}
          className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]">
          <option value="" disabled>Seleziona un mezzo</option>
          {vehicles.map((v) => <option key={v.id} value={v.id}>{v.plate}{v.model ? ` — ${v.model}` : ""}</option>)}
        </select>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Data *</label>
          <input required type="date" value={f.date} onChange={(e) => setF({ ...f, date: e.target.value })}
            className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
        </div>
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Stato</label>
          <select value={f.status} onChange={(e) => setF({ ...f, status: e.target.value })}
            className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]">
            {Object.entries(CARGO_STATUS_LABELS).map(([k, label]) => <option key={k} value={k}>{label}</option>)}
          </select>
        </div>
      </div>
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Descrizione carico *</label>
        <input required value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })}
          placeholder="Cosa viene trasportato"
          className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
      </div>
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Destinazione</label>
        <input value={f.destination} onChange={(e) => setF({ ...f, destination: e.target.value })}
          className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
      </div>
      {clients.length > 0 && (
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Cliente destinatario (opzionale)</label>
          <select value={f.client_id} onChange={(e) => setF({ ...f, client_id: e.target.value })}
            className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]">
            <option value="">Nessuno</option>
            {clients.map((c) => <option key={c.id} value={c.id}>{c.company_name}</option>)}
          </select>
        </div>
      )}
      {orders.length > 0 && (
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Ordine collegato (opzionale)</label>
          <select value={f.order_id} onChange={(e) => setF({ ...f, order_id: e.target.value })}
            className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]">
            <option value="">Nessuno</option>
            {orders.map((o) => <option key={o.id} value={o.id}>{o.numero_ordine || o.id.slice(0, 8)}</option>)}
          </select>
        </div>
      )}
      <div className="grid grid-cols-3 gap-3">
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Quantità</label>
          <input type="number" step="0.01" min="0" value={f.quantity} onChange={(e) => setF({ ...f, quantity: e.target.value })}
            className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
        </div>
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Colli</label>
          <input type="number" step="1" min="0" value={f.colli} onChange={(e) => setF({ ...f, colli: e.target.value })}
            className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
        </div>
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Peso (kg)</label>
          <input type="number" step="0.1" min="0" value={f.peso} onChange={(e) => setF({ ...f, peso: e.target.value })}
            className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
        </div>
      </div>
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Note</label>
        <textarea value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} rows={2}
          className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
      </div>
      <button type="submit" className="w-full bg-[#0A192F] text-white py-2.5 rounded-md text-[13px] font-medium">{submitLabel}</button>
    </form>
  );
}

function CargoSignatureForm({ load, onSign, onClose }) {
  const sigRef = useRef(null);
  const [signerName, setSignerName] = useState("");
  const [busy, setBusy] = useState(false);

  const clear = () => sigRef.current?.clear();

  const submit = async () => {
    if (!sigRef.current || sigRef.current.isEmpty()) {
      toast.error("Firma richiesta");
      return;
    }
    if (!signerName.trim()) {
      toast.error("Nome di chi riceve richiesto");
      return;
    }
    setBusy(true);
    try {
      const dataUrl = sigRef.current.getCanvas().toDataURL("image/png");
      await onSign(dataUrl, signerName.trim());
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="bg-[#F9F9F8] border border-[#E4E4E1] rounded-md p-4">
        <div className="font-mono text-[10px] uppercase tracking-widest text-[#6B6B72] mb-1">Consegna</div>
        <div className="font-cabinet font-bold text-[15px] leading-tight">{load.description}</div>
        <div className="text-[12px] text-[#52525B] mt-1">{load.vehicle_plate} · {load.date}{load.destination ? ` · ${load.destination}` : ""}</div>
      </div>

      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Nome di chi riceve *</label>
        <input value={signerName} onChange={(e) => setSignerName(e.target.value)}
          className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" placeholder="Nome e cognome" />
      </div>

      <div>
        <div className="flex items-center justify-between mb-1.5">
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B]">Firma qui sotto</label>
          <button onClick={clear} type="button" className="flex items-center gap-1 text-[11px] font-mono uppercase tracking-widest text-[#6B6B72] hover:text-[#DC2626]">
            <Eraser className="w-3 h-3" /> pulisci
          </button>
        </div>
        <div className="bg-white border-2 border-dashed border-[#E4E4E1] rounded-md overflow-hidden">
          <SignatureCanvas
            ref={sigRef}
            penColor="#0A192F"
            canvasProps={{ width: 480, height: 180, className: "w-full h-[180px] touch-none" }}
          />
        </div>
      </div>

      <div className="flex justify-end gap-2 pt-2 border-t border-[#E4E4E1]">
        <button onClick={onClose} type="button" className="px-4 py-2 border border-[#E4E4E1] rounded-md text-[13px] font-medium">Annulla</button>
        <button onClick={submit} disabled={busy}
          className="px-4 py-2 bg-[#0A192F] text-white rounded-md text-[13px] font-medium disabled:opacity-50">
          {busy ? "Firma in corso…" : "Firma consegna"}
        </button>
      </div>
    </div>
  );
}
