import { useState } from "react";
import { ShieldAlert, Check, Pencil, X, Loader2 } from "lucide-react";

const EXPENSE_CATEGORY_LABELS = {
  carburante: "Carburante", vitto: "Vitto", alloggio: "Alloggio",
  pedaggio_parcheggio: "Pedaggio/Parcheggio", materiali: "Materiali",
  inps: "INPS", enasarco: "ENASARCO", assicurazione_auto: "Assicurazione auto",
  commercialista: "Commercialista", altro: "Altro",
};

const fmt = (n) => new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(n || 0);

/**
 * Scheda di conferma mostrata prima di registrare un'operazione economica
 * (vendita/offerta, o spesa di importo elevato) proposta dall'AI — sia dalla
 * chat completa che dal pulsante microfono globale. L'operazione NON è ancora
 * stata scritta sul CRM quando questa scheda appare: viene scritta solo se
 * l'utente preme "Conferma".
 */
export default function AIActionConfirm({ action, onConfirm, onCancel, busy }) {
  const [mode, setMode] = useState("review"); // review | edit
  const [fields, setFields] = useState(() => ({ ...action.resolved_input }));

  const isOffer = action.tool_name === "add_offer";

  const handleConfirm = () => onConfirm(fields);

  return (
    <div data-testid="ai-action-confirm" className="border border-[#FED7AA] bg-[#FFF7ED] rounded-md p-4 space-y-3">
      <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest text-[#FF5A00]">
        <ShieldAlert className="w-3.5 h-3.5" /> Operazione da registrare
      </div>

      {mode === "review" ? (
        <div className="space-y-1.5 text-[13px]">
          {isOffer ? (
            <>
              <Row label="Cliente" value={fields.client_name} />
              <Row label="Mandante" value={fields.mandante_name} />
              <Row label="Titolo" value={fields.title} />
              <Row label="Importo" value={<span className="font-cabinet font-bold">{fmt(fields.amount)}</span>} />
              <Row label="Stato" value={fields.accepted ? "accettata" : "bozza"} />
            </>
          ) : (
            <>
              <Row label="Categoria" value={EXPENSE_CATEGORY_LABELS[fields.category] || fields.category} />
              <Row label="Importo" value={<span className="font-cabinet font-bold">{fmt(fields.amount)}</span>} />
              <Row label="Data" value={fields.date} />
              {fields.description && <Row label="Descrizione" value={fields.description} />}
            </>
          )}
        </div>
      ) : (
        <div className="space-y-2.5">
          {isOffer ? (
            <>
              <div className="text-[12px] text-[#52525B]">
                Cliente: <span className="font-medium text-[#0A0A0A]">{fields.client_name}</span> · Mandante:{" "}
                <span className="font-medium text-[#0A0A0A]">{fields.mandante_name}</span>
              </div>
              <EditField label="Importo (€)" type="number" value={fields.amount}
                onChange={(v) => setFields({ ...fields, amount: parseFloat(v) || 0 })} />
              <div>
                <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1">Stato</label>
                <select value={fields.accepted ? "accettata" : "bozza"}
                  onChange={(e) => setFields({ ...fields, accepted: e.target.value === "accettata" })}
                  className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]">
                  <option value="bozza">Bozza (solo preventivo)</option>
                  <option value="accettata">Accettata (genera anche l'ordine e la provvigione)</option>
                </select>
              </div>
            </>
          ) : (
            <>
              <EditField label="Importo (€)" type="number" value={fields.amount}
                onChange={(v) => setFields({ ...fields, amount: parseFloat(v) || 0 })} />
              <div>
                <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1">Categoria</label>
                <select value={fields.category} onChange={(e) => setFields({ ...fields, category: e.target.value })}
                  className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]">
                  {Object.entries(EXPENSE_CATEGORY_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </div>
              <EditField label="Data" type="date" value={fields.date} onChange={(v) => setFields({ ...fields, date: v })} />
              <EditField label="Descrizione" type="text" value={fields.description} onChange={(v) => setFields({ ...fields, description: v })} />
            </>
          )}
        </div>
      )}

      <div className="flex items-center gap-2 pt-1">
        <button
          data-testid="ai-action-confirm-btn"
          onClick={handleConfirm}
          disabled={busy}
          className="flex items-center gap-1.5 px-3 py-2 bg-[#0A192F] text-white rounded-md text-[12px] font-medium disabled:opacity-50"
        >
          {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
          Conferma
        </button>
        {mode === "review" ? (
          <button onClick={() => setMode("edit")} disabled={busy}
            className="flex items-center gap-1.5 px-3 py-2 border border-[#E4E4E1] rounded-md text-[12px] font-medium text-[#52525B] disabled:opacity-50">
            <Pencil className="w-3.5 h-3.5" /> Modifica
          </button>
        ) : (
          <button onClick={() => setMode("review")} disabled={busy}
            className="flex items-center gap-1.5 px-3 py-2 border border-[#E4E4E1] rounded-md text-[12px] font-medium text-[#52525B] disabled:opacity-50">
            Fatto
          </button>
        )}
        <button
          data-testid="ai-action-cancel-btn"
          onClick={onCancel}
          disabled={busy}
          className="flex items-center gap-1.5 px-3 py-2 text-[#A1A1AA] hover:text-red-500 rounded-md text-[12px] font-medium disabled:opacity-50 ml-auto"
        >
          <X className="w-3.5 h-3.5" /> Annulla
        </button>
      </div>
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-[#52525B]">{label}</span>
      <span className="text-[#0A0A0A] text-right">{value}</span>
    </div>
  );
}

function EditField({ label, type, value, onChange }) {
  return (
    <div>
      <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1">{label}</label>
      <input type={type} value={value ?? ""} onChange={(e) => onChange(e.target.value)} step={type === "number" ? "0.01" : undefined}
        className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
    </div>
  );
}
