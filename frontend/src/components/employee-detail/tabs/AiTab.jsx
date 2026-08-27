import { useState } from "react";
import { Sparkles } from "lucide-react";
import api from "../../../api";

function localSummaryText(summary) {
  if (!summary) return "";
  const { ferie, permessi, malattie } = summary;
  const parts = [`Ferie residue: ${ferie.residue} giorni`];
  if (permessi.ore_approvate) parts.push(`Permessi approvati: ${permessi.ore_approvate} ore`);
  if (malattie.giorni) parts.push(`Malattie registrate: ${malattie.giorni} giorni`);
  return parts.join(". ") + ".";
}

export default function AiTab({ employeeId, summary }) {
  const [aiSummary, setAiSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const generate = async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get(`/employees/${employeeId}/ai-summary`);
      if (data.summary) {
        setAiSummary(data.summary);
      } else {
        setError("Assistente AI non configurato per questo account.");
      }
    } catch (err) {
      setError(err?.response?.status === 429
        ? "Troppe richieste, riprova tra qualche minuto."
        : "Impossibile generare il riepilogo al momento.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="bg-white border border-[#E4E4E1] rounded-md p-4">
        <div className="font-mono text-[10px] uppercase tracking-widest text-[#6B6B72] mb-2">Riepilogo</div>
        <p className="text-[13px] text-[#0A192F] leading-relaxed">{localSummaryText(summary)}</p>
      </div>

      {!aiSummary && !loading && !error && (
        <div className="bg-white border border-[#E4E4E1] rounded-md p-6 text-center">
          <Sparkles className="w-6 h-6 text-[#6B6B72] mx-auto mb-2" />
          <p className="text-[13px] text-[#52525B] mb-1">Genera un riepilogo in linguaggio naturale della situazione di questo dipendente.</p>
          <p className="text-[11px] text-[#6B6B72] mb-4">Invia questi valori a un servizio AI esterno (Anthropic) per generare il testo.</p>
          <button onClick={generate} className="px-4 py-2.5 bg-[#0A192F] text-white rounded-md text-[13px] font-medium">
            Genera riepilogo AI
          </button>
        </div>
      )}
      {loading && (
        <div className="bg-white border border-[#E4E4E1] rounded-md p-6 text-center text-[#6B6B72] text-[13px]">Generazione in corso…</div>
      )}
      {error && !loading && (
        <div className="bg-white border border-[#E4E4E1] rounded-md p-6 text-center">
          <p className="text-[13px] text-[#DC2626] mb-3">{error}</p>
          <button onClick={generate} className="px-3 py-2 border border-[#E4E4E1] rounded-md text-[12px] font-medium hover:border-[#0A192F]">Riprova</button>
        </div>
      )}
      {aiSummary && !loading && (
        <div className="bg-[#F9F9F8] border border-[#E4E4E1] rounded-md p-4">
          <div className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-widest text-[#6B6B72] mb-2">
            <Sparkles className="w-3 h-3" /> Riepilogo AI
          </div>
          <p className="text-[13px] text-[#0A192F] leading-relaxed">{aiSummary}</p>
          <button onClick={generate} className="mt-3 text-[12px] font-medium text-[#52525B] hover:text-[#0A192F]">Rigenera</button>
        </div>
      )}
    </div>
  );
}
