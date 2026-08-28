import { Coins } from "lucide-react";

// Provvigioni inserite manualmente: si sommano al totale calcolato dagli
// ordini — per provvigioni concluse fuori dal flusso ordini del CRM. Più
// righe possono coesistere sullo stesso mese (es. un premio per un
// mandante e una rettifica per un altro). Contano a tutti gli effetti come
// provvigioni reali (dashboard, obiettivi, briefing AI, export CSV,
// dettaglio cliente), non solo su questa pagina.
export default function ManualCommissionForm({
  manualForm, setManualForm, editingManualId, startNewManualEntry, saveManualCommission, savingManual,
  mandanti, clients,
}) {
  return (
    <div className="bg-white border border-[#E4E4E1] rounded-md p-5 mb-6">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Coins className="w-4 h-4 text-[#B23E00]" />
          <span className="font-mono text-[11px] uppercase tracking-widest text-[#52525B]">
            {editingManualId ? "Modifica provvigione manuale" : "Nuova provvigione manuale"}
          </span>
        </div>
        {editingManualId && (
          <button onClick={startNewManualEntry} className="font-mono text-[10px] uppercase tracking-widest text-[#6B6B72] hover:text-[#0A192F]">
            Annulla modifica
          </button>
        )}
      </div>
      <p className="text-[12px] text-[#52525B] mb-3">
        Per provvigioni non tracciate tramite gli ordini del CRM. Si sommano al totale generato.
      </p>
      <div className="flex flex-wrap items-end gap-3 mb-3">
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Mese</label>
          <input
            type="month"
            value={manualForm.period}
            onChange={(e) => setManualForm((f) => ({ ...f, period: e.target.value }))}
            className="bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]"
          />
        </div>
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Importo (€)</label>
          <input
            type="number" step="0.01" min="0.01" value={manualForm.amount}
            onChange={(e) => setManualForm((f) => ({ ...f, amount: e.target.value }))}
            placeholder="0,00"
            className="bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px] w-32"
          />
        </div>
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Mandante</label>
          <select
            value={manualForm.mandante_id}
            onChange={(e) => setManualForm((f) => ({ ...f, mandante_id: e.target.value }))}
            className="bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]"
          >
            <option value="">Nessun mandante</option>
            {[...mandanti].sort((a, b) => a.name.localeCompare(b.name)).map((m) => (
              <option key={m.id} value={m.id}>{m.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Cliente</label>
          <select
            value={manualForm.client_id}
            onChange={(e) => setManualForm((f) => ({ ...f, client_id: e.target.value }))}
            className="bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]"
          >
            <option value="">Nessun cliente</option>
            {[...clients].sort((a, b) => (a.company_name || "").localeCompare(b.company_name || "")).map((cl) => (
              <option key={cl.id} value={cl.id}>{cl.company_name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Stato</label>
          <select
            value={manualForm.stato}
            onChange={(e) => setManualForm((f) => ({ ...f, stato: e.target.value }))}
            className="bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]"
          >
            <option value="maturato">Maturato</option>
            <option value="incassato">Incassato</option>
          </select>
        </div>
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Tipo</label>
          <select
            value={manualForm.tipo}
            onChange={(e) => setManualForm((f) => ({ ...f, tipo: e.target.value }))}
            className="bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]"
          >
            <option value="ordinaria">Ordinaria</option>
            <option value="bonus">Bonus</option>
            <option value="rettifica">Rettifica</option>
          </select>
        </div>
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Descrizione</label>
          <input
            type="text" value={manualForm.descrizione}
            onChange={(e) => setManualForm((f) => ({ ...f, descrizione: e.target.value }))}
            placeholder="Es. accordo fuori sistema"
            className="bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px] w-56"
          />
        </div>
        <button
          onClick={saveManualCommission}
          disabled={savingManual}
          className="px-4 py-2 bg-[#0A192F] text-white rounded-md text-[13px] font-medium disabled:opacity-50"
        >
          {editingManualId ? "Aggiorna" : "Aggiungi"}
        </button>
      </div>
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Note</label>
        <textarea
          value={manualForm.note}
          onChange={(e) => setManualForm((f) => ({ ...f, note: e.target.value }))}
          rows={2}
          placeholder="Dettagli facoltativi"
          className="bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px] w-full max-w-xl"
        />
      </div>
    </div>
  );
}
