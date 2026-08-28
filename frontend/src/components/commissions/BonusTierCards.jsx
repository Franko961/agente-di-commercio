import { Trophy, ChevronRight } from "lucide-react";
import { fmt } from "./constants";

export default function BonusTierCards({ bonusSummary }) {
  if (bonusSummary.length === 0) return null;

  return (
    <div className="mb-6">
      <div className="flex items-center gap-2 mb-3">
        <Trophy className="w-4 h-4 text-[#B23E00]" />
        <span className="font-mono text-[11px] uppercase tracking-widest text-[#52525B]">Scala premi maturati</span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {bonusSummary.map(b => {
          const sorted = [...b.tiers].sort((a, b) => a.threshold - b.threshold);
          const maxThreshold = sorted[sorted.length - 1]?.threshold || 1;
          const progress = Math.min((b.fatturato / maxThreshold) * 100, 100);
          const nextThreshold = b.next_tier?.threshold;
          const toNext = nextThreshold ? nextThreshold - b.fatturato : 0;

          return (
            <div key={b.mandante_id} className="bg-white border border-[#E4E4E1] rounded-md p-5">
              {/* Header */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-md flex items-center justify-center text-white text-[12px] font-black font-cabinet"
                    style={{ background: b.brand_color }}>
                    {b.mandante_name[0]}
                  </div>
                  <span className="font-cabinet font-bold text-[15px]">{b.mandante_name}</span>
                </div>
                <div className="text-right">
                  <div className="font-mono text-[10px] uppercase tracking-widest text-[#6B6B72]">Bonus totale</div>
                  <div className="font-cabinet font-black text-xl text-[#059669]">{fmt(b.total_bonus)}</div>
                </div>
              </div>

              {/* Fatturato + barra progresso */}
              <div className="mb-3">
                <div className="flex justify-between text-[12px] mb-1.5">
                  <span className="text-[#52525B]">Fatturato attuale</span>
                  <span className="font-cabinet font-bold">{fmt(b.fatturato)}</span>
                </div>
                <div className="w-full bg-[#F3F3F1] rounded-full h-2">
                  <div className="h-2 rounded-full bg-[#B23E00] transition-all"
                    style={{ width: `${progress}%` }} />
                </div>
                {b.next_tier && (
                  <div className="text-[11px] text-[#6B6B72] mt-1.5 flex items-center gap-1">
                    <ChevronRight className="w-3 h-3" />
                    Mancano {fmt(toNext)} per il prossimo premio di {fmt(b.next_tier.bonus)}
                  </div>
                )}
                {!b.next_tier && b.tiers.length > 0 && (
                  <div className="text-[11px] text-[#059669] mt-1.5 font-medium">🏆 Tutti gli scaglioni raggiunti!</div>
                )}
              </div>

              {/* Scaglioni */}
              <div className="space-y-1 border-t border-[#E4E4E1] pt-3">
                {sorted.map((t, i) => {
                  const reached = b.fatturato >= t.threshold;
                  return (
                    <div key={i} className={`flex justify-between items-center text-[12px] ${reached ? "opacity-100" : "opacity-40"}`}>
                      <div className="flex items-center gap-1.5">
                        <div className={`w-2 h-2 rounded-full ${reached ? "bg-[#059669]" : "bg-[#E4E4E1]"}`} />
                        <span className="text-[#52525B]">≥ {fmt(t.threshold)}</span>
                      </div>
                      <span className={`font-cabinet font-bold ${reached ? "text-[#059669]" : "text-[#6B6B72]"}`}>
                        +{fmt(t.bonus)}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
