import { useState } from "react";
import { useNavigate } from "react-router-dom";
import * as XLSX from "xlsx";
import { Upload, FileSpreadsheet, ArrowLeft, CheckCircle2, AlertTriangle, Loader2 } from "lucide-react";
import { toast } from "sonner";
import api from "../api";

// Limiti applicati PRIMA di passare il file alla libreria xlsx: il parsing
// avviene interamente nel browser di chi importa (mai sul server), quindi
// un file enorme o con troppe righe non mette a rischio nessun altro
// utente — ma può comunque bloccare per diversi secondi/minuti (o far
// esaurire la memoria) la scheda di CHI lo sta importando. 10 MB è
// generoso per un elenco clienti in CSV/Excel; MAX_ROWS è lo stesso limite
// già applicato lato server su POST /api/clients/bulk (vedi
// backend/core/validation_limits.py MAX_BULK_IMPORT_ITEMS) — fermarsi qui
// evita di far leggere/mappare all'utente migliaia di righe che verrebbero
// comunque rifiutate in blocco all'invio.
const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024;
const MAX_ROWS = 2000;

// Campi del cliente che l'import può popolare, con etichetta per la UI di mappatura.
const FIELDS = [
  { key: "", label: "— ignora colonna —" },
  { key: "company_name", label: "Ragione sociale *" },
  { key: "contact_name", label: "Referente" },
  { key: "email", label: "Email" },
  { key: "phone", label: "Telefono" },
  { key: "vat_number", label: "Partita IVA" },
  { key: "address", label: "Indirizzo" },
  { key: "city", label: "Città" },
  { key: "province", label: "Provincia" },
  { key: "zone", label: "Zona / Regione" },
  { key: "sector", label: "Settore merceologico" },
  { key: "potential", label: "Potenziale" },
  { key: "notes", label: "Note" },
  { key: "mandante_names", label: "Mandante/i (nomi separati da virgola)" },
];

// Normalizza un'intestazione di colonna per il riconoscimento automatico:
// minuscolo, senza accenti, senza spazi/punteggiatura — così "P. IVA",
// "Partita Iva" e "piva" finiscono tutti sulla stessa chiave.
const normalize = (s) =>
  (s || "").toString().trim().toLowerCase()
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]/g, "");

const AUTO_MAP = {
  ragionesociale: "company_name", azienda: "company_name", nomeazienda: "company_name",
  societa: "company_name", denominazione: "company_name", cliente: "company_name",
  referente: "contact_name", contatto: "contact_name", persona: "contact_name",
  email: "email", mail: "email", posta: "email", indirizzoemail: "email",
  telefono: "phone", tel: "phone", cellulare: "phone", phone: "phone",
  piva: "vat_number", partitaiva: "vat_number", vat: "vat_number", vatnumber: "vat_number",
  indirizzo: "address", via: "address", indirizzosede: "address",
  citta: "city", comune: "city",
  provincia: "province", prov: "province",
  zona: "zone", regione: "zone", areacommerciale: "zone",
  settore: "sector", settoremerceologico: "sector", categoria: "sector",
  potenziale: "potential",
  note: "notes", notes: "notes", annotazioni: "notes",
  mandante: "mandante_names", mandanti: "mandante_names", fornitore: "mandante_names", fornitori: "mandante_names",
};

export default function ImportClienti() {
  const navigate = useNavigate();
  const [fileName, setFileName] = useState("");
  const [headers, setHeaders] = useState([]);
  const [rows, setRows] = useState([]);
  const [mapping, setMapping] = useState({});
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState(null);

  const handleFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > MAX_FILE_SIZE_BYTES) {
      toast.error(`Il file supera i ${MAX_FILE_SIZE_BYTES / (1024 * 1024)} MB consentiti`);
      e.target.value = "";
      return;
    }
    setResult(null);
    setFileName(file.name);
    try {
      const buf = await file.arrayBuffer();
      // cellFormula NON richiesto (default): le formule non vengono mai
      // valutate né lette come codice, solo i valori già calcolati/salvati
      // nel file — non c'è nulla da eseguire.
      const wb = XLSX.read(buf, { type: "array" });
      const sheet = wb.Sheets[wb.SheetNames[0]];
      const data = XLSX.utils.sheet_to_json(sheet, { defval: "", raw: false });
      if (!data.length) {
        toast.error("Il file sembra vuoto o senza righe leggibili");
        return;
      }
      if (data.length > MAX_ROWS) {
        toast.error(`Il file ha ${data.length} righe, il massimo consentito è ${MAX_ROWS}. Dividilo in più file più piccoli.`);
        e.target.value = "";
        return;
      }
      const cols = Object.keys(data[0]);
      const guessed = {};
      cols.forEach((c) => {
        const key = AUTO_MAP[normalize(c)];
        if (key) guessed[c] = key;
      });
      setHeaders(cols);
      setMapping(guessed);
      setRows(data);
    } catch {
      toast.error("Impossibile leggere il file — assicurati che sia un CSV o Excel valido");
    }
  };

  const setColumnMapping = (col, field) => setMapping((prev) => ({ ...prev, [col]: field }));

  const mappedRows = rows.map((row) => {
    const item = {};
    for (const [col, field] of Object.entries(mapping)) {
      if (field) item[field] = (row[col] ?? "").toString().trim();
    }
    return item;
  });

  const companyNameMapped = Object.values(mapping).includes("company_name");
  const missingCompanyName = mappedRows.filter((r) => !r.company_name).length;

  const doImport = async () => {
    setImporting(true);
    try {
      const { data } = await api.post("/clients/bulk", { clients: mappedRows });
      setResult(data);
      if (data.imported > 0) {
        toast.success(`${data.imported} clienti importati`);
      } else {
        toast.info("Nessun cliente importato — controlla i dettagli sotto");
      }
    } catch {
      toast.error("Errore durante l'importazione");
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="p-4 md:p-8 max-w-4xl">
      <button onClick={() => navigate("/app/clienti")} className="flex items-center gap-1.5 text-[12px] font-mono uppercase tracking-widest text-[#52525B] hover:text-[#0A192F] mb-4">
        <ArrowLeft className="w-3.5 h-3.5" /> Torna ai clienti
      </button>

      <div className="border-b border-[#E4E4E1] pb-6 mb-6">
        <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#FF5A00] mb-2">Anagrafiche</div>
        <h1 className="font-cabinet font-black text-3xl md:text-4xl tracking-tight">Importa clienti</h1>
        <p className="text-[#52525B] text-[14px] mt-2">
          Carica un file CSV o Excel con l'elenco dei tuoi clienti. Puoi verificare e correggere la corrispondenza delle colonne prima di importare.
        </p>
      </div>

      {!rows.length ? (
        <label className="flex flex-col items-center justify-center gap-3 border-2 border-dashed border-[#E4E4E1] rounded-lg p-12 cursor-pointer hover:border-[#FF5A00] transition-colors bg-white">
          <Upload className="w-8 h-8 text-[#A1A1AA]" />
          <div className="text-[14px] font-medium">Clicca per scegliere un file .csv, .xlsx o .xls</div>
          <div className="text-[12px] text-[#A1A1AA]">La prima riga deve contenere le intestazioni delle colonne</div>
          <input type="file" accept=".csv,.xlsx,.xls" onChange={handleFile} className="hidden" />
        </label>
      ) : (
        <div className="space-y-5">
          <div className="flex items-center gap-2 text-[13px] text-[#52525B]">
            <FileSpreadsheet className="w-4 h-4 text-[#FF5A00]" />
            <span className="font-medium">{fileName}</span>
            <span>· {rows.length} righe trovate</span>
            <button onClick={() => { setRows([]); setHeaders([]); setMapping({}); setResult(null); }}
                    className="ml-auto text-[12px] font-mono uppercase tracking-widest text-[#A1A1AA] hover:text-[#DC2626]">
              cambia file
            </button>
          </div>

          <div className="bg-white border border-[#E4E4E1] rounded-lg p-4">
            <div className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] mb-3">
              Corrispondenza colonne (verifica prima di importare)
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {headers.map((col) => (
                <div key={col} className="flex items-center gap-2">
                  <div className="w-1/2 text-[12px] font-medium truncate" title={col}>{col}</div>
                  <select
                    value={mapping[col] || ""}
                    onChange={(e) => setColumnMapping(col, e.target.value)}
                    className="w-1/2 bg-white border border-[#E4E4E1] rounded-md px-2 py-1.5 text-[12px]"
                  >
                    {FIELDS.map((f) => <option key={f.key} value={f.key}>{f.label}</option>)}
                  </select>
                </div>
              ))}
            </div>
            {!companyNameMapped && (
              <div className="mt-3 flex items-center gap-1.5 text-[12px] text-[#DC2626]">
                <AlertTriangle className="w-3.5 h-3.5" /> Nessuna colonna è mappata su "Ragione sociale" — è obbligatoria per importare.
              </div>
            )}
            {companyNameMapped && missingCompanyName > 0 && (
              <div className="mt-3 flex items-center gap-1.5 text-[12px] text-[#B45309]">
                <AlertTriangle className="w-3.5 h-3.5" /> {missingCompanyName} righe hanno la ragione sociale vuota e verranno saltate.
              </div>
            )}
          </div>

          <div className="bg-white border border-[#E4E4E1] rounded-lg p-4 overflow-x-auto">
            <div className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] mb-3">Anteprima (prime 5 righe)</div>
            <table className="w-full text-[12px]">
              <thead>
                <tr className="text-left text-[#A1A1AA] font-mono text-[10px] uppercase">
                  {headers.map((h) => <th key={h} className="pb-2 pr-4 whitespace-nowrap">{mapping[h] ? FIELDS.find(f => f.key === mapping[h])?.label : h}</th>)}
                </tr>
              </thead>
              <tbody>
                {rows.slice(0, 5).map((r, i) => (
                  <tr key={i} className="border-t border-[#E4E4E1]">
                    {headers.map((h) => <td key={h} className="py-1.5 pr-4 whitespace-nowrap">{r[h]}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <button
            onClick={doImport}
            disabled={importing || !companyNameMapped}
            className="flex items-center gap-2 bg-[#0A192F] hover:bg-[#172A45] text-white px-5 py-2.5 rounded-md text-[13px] font-medium disabled:opacity-50"
          >
            {importing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
            {importing ? "Importazione in corso…" : `Importa ${rows.length} clienti`}
          </button>

          {result && (
            <div className="bg-white border border-[#E4E4E1] rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <CheckCircle2 className="w-4 h-4 text-[#059669]" />
                <span className="font-cabinet font-bold text-[15px]">{result.imported} clienti importati</span>
                <span className="text-[12px] text-[#A1A1AA]">su {result.total} righe totali</span>
              </div>
              {result.skipped.length > 0 && (
                <div className="mt-3">
                  <div className="font-mono text-[10px] uppercase tracking-widest text-[#B45309] mb-2">
                    {result.skipped.length} righe saltate
                  </div>
                  <div className="max-h-48 overflow-y-auto space-y-1">
                    {result.skipped.map((s, i) => (
                      <div key={i} className="text-[12px] text-[#52525B] flex items-center gap-2">
                        <span className="font-mono text-[10px] text-[#A1A1AA]">riga {s.row}</span>
                        <span className="font-medium">{s.company_name || "(senza nome)"}</span>
                        <span className="text-[#A1A1AA]">— {s.reason}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {result.imported > 0 && (
                <button onClick={() => navigate("/app/clienti")} className="mt-4 text-[12px] font-mono uppercase tracking-widest text-[#FF5A00]">
                  Vai all'elenco clienti →
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
