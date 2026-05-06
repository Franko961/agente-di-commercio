import { useRef, useState } from "react";
import SignatureCanvas from "react-signature-canvas";
import { Eraser, Check, Download } from "lucide-react";
import { jsPDF } from "jspdf";

const fmt = (n) => new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(n || 0);

export default function SignaturePad({ offer, client, mandante, onSign, onClose }) {
  const sigRef = useRef(null);
  const [signerName, setSignerName] = useState(client?.contact_name || "");
  const [busy, setBusy] = useState(false);

  const clear = () => sigRef.current?.clear();

  const generatePDF = (signatureDataUrl, signedAt) => {
    const doc = new jsPDF({ unit: "mm", format: "a4" });
    const w = doc.internal.pageSize.getWidth();

    // Header
    doc.setFillColor(10, 25, 47);
    doc.rect(0, 0, w, 28, "F");
    doc.setTextColor(255, 90, 0);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(20);
    doc.text("AGENTE.", 14, 15);
    doc.setTextColor(255, 255, 255);
    doc.setFontSize(9);
    doc.setFont("helvetica", "normal");
    doc.text("OFFERTA COMMERCIALE", 14, 22);

    // Title
    doc.setTextColor(10, 10, 10);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(16);
    doc.text(offer.title, 14, 42);

    // Meta block
    doc.setFontSize(9);
    doc.setFont("helvetica", "normal");
    doc.setTextColor(82, 82, 91);
    let y = 52;
    doc.text(`Cliente: ${client?.company_name || "-"}`, 14, y); y += 5;
    if (client?.contact_name) { doc.text(`Referente: ${client.contact_name}`, 14, y); y += 5; }
    if (client?.address) { doc.text(`Indirizzo: ${client.address}, ${client.city || ""}`, 14, y); y += 5; }
    if (mandante) { doc.text(`Mandante: ${mandante.name}`, 14, y); y += 5; }
    doc.text(`Data: ${new Date().toLocaleDateString("it-IT")}`, 14, y); y += 5;
    if (offer.expires_at) { doc.text(`Scadenza: ${new Date(offer.expires_at).toLocaleDateString("it-IT")}`, 14, y); y += 5; }

    // Items table
    y += 6;
    doc.setFillColor(243, 243, 241);
    doc.rect(10, y - 4, w - 20, 8, "F");
    doc.setTextColor(10, 10, 10);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(9);
    doc.text("DESCRIZIONE", 14, y);
    doc.text("QTA", 110, y, { align: "right" });
    doc.text("PREZZO", 140, y, { align: "right" });
    doc.text("SCONTO", 165, y, { align: "right" });
    doc.text("TOTALE", w - 14, y, { align: "right" });
    y += 6;
    doc.setFont("helvetica", "normal");

    (offer.items || []).forEach((it) => {
      const sub = (it.quantity || 0) * (it.unit_price || 0) * (1 - (it.discount || 0) / 100);
      doc.text(it.description || "—", 14, y);
      doc.text(String(it.quantity || 0), 110, y, { align: "right" });
      doc.text(fmt(it.unit_price), 140, y, { align: "right" });
      doc.text(`${it.discount || 0}%`, 165, y, { align: "right" });
      doc.text(fmt(sub), w - 14, y, { align: "right" });
      y += 6;
    });

    // Total
    y += 4;
    doc.setDrawColor(228, 228, 225);
    doc.line(10, y, w - 10, y);
    y += 8;
    doc.setFont("helvetica", "bold");
    doc.setFontSize(14);
    doc.setTextColor(10, 25, 47);
    doc.text("TOTALE OFFERTA", 14, y);
    doc.setTextColor(255, 90, 0);
    doc.text(fmt(offer.total), w - 14, y, { align: "right" });

    // Signature block
    y += 24;
    doc.setDrawColor(228, 228, 225);
    doc.rect(10, y, w - 20, 60);
    doc.setFontSize(8);
    doc.setFont("helvetica", "normal");
    doc.setTextColor(82, 82, 91);
    doc.text("FIRMA DEL CLIENTE PER ACCETTAZIONE", 14, y + 6);
    if (signatureDataUrl) {
      try { doc.addImage(signatureDataUrl, "PNG", 14, y + 10, 80, 35); } catch (e) {}
    }
    doc.setTextColor(10, 10, 10);
    doc.setFont("helvetica", "bold");
    doc.text(signerName || client?.contact_name || "—", 14, y + 52);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(7);
    doc.setTextColor(161, 161, 170);
    doc.text(`Firmato il ${new Date(signedAt).toLocaleString("it-IT")}`, 14, y + 56);

    // Footer
    doc.setFontSize(7);
    doc.setTextColor(161, 161, 170);
    doc.text("Generato da AGENTE — Gestionale per agenti di commercio", w / 2, 290, { align: "center" });

    doc.save(`offerta-${offer.title.replace(/[^a-z0-9]/gi, "-").toLowerCase()}.pdf`);
  };

  const submit = async () => {
    if (!sigRef.current || sigRef.current.isEmpty()) {
      alert("Firma richiesta");
      return;
    }
    setBusy(true);
    const dataUrl = sigRef.current.getCanvas().toDataURL("image/png");
    const signedAt = new Date().toISOString();
    try {
      await onSign(dataUrl, signerName);
      generatePDF(dataUrl, signedAt);
      onClose();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="bg-[#F9F9F8] border border-[#E4E4E1] rounded-md p-4">
        <div className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA] mb-1">Stai firmando</div>
        <div className="font-cabinet font-bold text-lg leading-tight">{offer.title}</div>
        <div className="text-[12px] text-[#52525B] mt-1">{client?.company_name} · {fmt(offer.total)}</div>
      </div>

      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Nome firmatario</label>
        <input
          data-testid="signer-name-input"
          value={signerName} onChange={(e) => setSignerName(e.target.value)}
          className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px] focus:outline-none focus:border-[#0A192F]"
          placeholder="Nome e cognome"
        />
      </div>

      <div>
        <div className="flex items-center justify-between mb-1.5">
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B]">Firma qui sotto</label>
          <button onClick={clear} type="button" className="flex items-center gap-1 text-[11px] font-mono uppercase tracking-widest text-[#A1A1AA] hover:text-[#DC2626]">
            <Eraser className="w-3 h-3" /> pulisci
          </button>
        </div>
        <div className="bg-white border-2 border-dashed border-[#E4E4E1] rounded-md overflow-hidden">
          <SignatureCanvas
            ref={sigRef}
            penColor="#0A192F"
            canvasProps={{
              width: 560, height: 200,
              className: "w-full h-[200px] touch-none",
              "data-testid": "signature-canvas",
            }}
          />
        </div>
        <div className="font-mono text-[10px] text-[#A1A1AA] mt-2">Usa il dito o il mouse per firmare. Verrà generato un PDF con la firma.</div>
      </div>

      <div className="flex justify-end gap-2 pt-2 border-t border-[#E4E4E1]">
        <button onClick={onClose} type="button" className="px-4 py-2 border border-[#E4E4E1] rounded-md text-[13px] font-medium">Annulla</button>
        <button
          data-testid="confirm-sign-button"
          onClick={submit} disabled={busy}
          className="px-4 py-2 bg-[#0A192F] hover:bg-[#172A45] text-white rounded-md text-[13px] font-medium flex items-center gap-2 disabled:opacity-50"
        >
          <Check className="w-4 h-4 text-[#FF5A00]" />
          {busy ? "Firma in corso…" : "Firma e genera PDF"}
        </button>
      </div>
    </div>
  );
}
