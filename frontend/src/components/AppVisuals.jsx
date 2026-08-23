import { Sparkles, Zap, ShieldCheck, Download, Trash2, CheckCircle2, Circle } from "lucide-react";

// Ricostruzioni stilizzate delle schermate reali dell'app (stessi
// colori/layout, dati di esempio) — non screenshot veri. Usate sia dal tour
// guidato pubblico (/tour) sia dal centro assistenza in-app (/app/aiuto),
// per non duplicare lo stesso disegno in due punti diversi.

export function MockupFrame({ children }) {
  return (
    <div className="bg-white rounded-xl border border-[#E4E4E1] shadow-xl overflow-hidden w-full max-w-sm mx-auto md:mx-0">
      <div className="flex items-center gap-1.5 px-3 py-2 bg-[#F3F3F1] border-b border-[#E4E4E1]">
        <div className="w-2 h-2 rounded-full bg-[#DC2626]" />
        <div className="w-2 h-2 rounded-full bg-[#B23E00]" />
        <div className="w-2 h-2 rounded-full bg-[#059669]" />
      </div>
      <div className="p-4 bg-[#F9F9F8] min-h-[260px] flex flex-col justify-center">
        {children}
      </div>
    </div>
  );
}

export function IniziareVisual() {
  const steps = [
    ["Crea un mandante", true],
    ["Aggiungi i tuoi clienti", true],
    ["Imposta gli obiettivi mensili", false],
  ];
  return (
    <MockupFrame>
      <div className="bg-white border border-[#E4E4E1] rounded-md p-3 space-y-2.5">
        {steps.map(([label, done]) => (
          <div key={label} className="flex items-center gap-2">
            {done
              ? <CheckCircle2 className="w-4 h-4 text-[#059669] shrink-0" />
              : <Circle className="w-4 h-4 text-[#E4E4E1] shrink-0" />}
            <span className={`text-[11px] ${done ? "text-[#6B6B72] line-through" : "text-[#0A0A0A] font-medium"}`}>{label}</span>
          </div>
        ))}
      </div>
    </MockupFrame>
  );
}

export function DashboardVisual() {
  return (
    <MockupFrame>
      <div className="grid grid-cols-3 gap-2 mb-3">
        {[["7", "Visite"], ["2", "Scadenze"], ["€180", "Obiettivo"]].map(([v, l]) => (
          <div key={l} className="bg-white border border-[#E4E4E1] rounded-md p-2 text-center">
            <div className="font-cabinet font-black text-lg">{v}</div>
            <div className="text-[9px] text-[#52525B] font-mono uppercase tracking-widest">{l}</div>
          </div>
        ))}
      </div>
      <div className="bg-[#FFF7ED] border border-[#FED7AA] rounded-md p-2.5 flex items-start gap-2 mb-3">
        <Sparkles className="w-3.5 h-3.5 text-[#B23E00] shrink-0 mt-0.5" />
        <div className="text-[11px] text-[#0A0A0A]">Visita prima Rossi Spa: l'offerta scade venerdì.</div>
      </div>
      <div className="bg-white border border-[#E4E4E1] rounded-md p-2.5">
        <div className="flex justify-between text-[10px] font-mono uppercase text-[#52525B] mb-1">
          <span>Fatturato del mese</span><span>72%</span>
        </div>
        <div className="h-1.5 bg-[#F3F3F1] rounded-full overflow-hidden">
          <div className="h-full bg-[#B23E00]" style={{ width: "72%" }} />
        </div>
      </div>
    </MockupFrame>
  );
}

export function ClientiVisual() {
  const clients = [
    ["RS", "Rossi Spa", "Ancona", "alto"],
    ["BT", "Bianchi Tessuti", "Pesaro", "medio"],
    ["CA", "Caffè Aurora", "Fermo", "alto"],
  ];
  return (
    <MockupFrame>
      <div className="space-y-2">
        {clients.map(([init, name, city, pot]) => (
          <div key={name} className="bg-white border border-[#E4E4E1] rounded-md p-2.5 flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-[#0A192F] text-white flex items-center justify-center font-cabinet font-bold text-[11px] shrink-0">{init}</div>
            <div className="min-w-0 flex-1">
              <div className="font-cabinet font-bold text-[12px] truncate">{name}</div>
              <div className="text-[10px] text-[#52525B]">{city}</div>
            </div>
            <div className={`text-[8px] font-mono uppercase px-1.5 py-0.5 rounded shrink-0 ${pot === "alto" ? "bg-[#05966915] text-[#059669]" : "bg-[#B23E0015] text-[#B23E00]"}`}>{pot}</div>
          </div>
        ))}
      </div>
    </MockupFrame>
  );
}

export function LeadVisual() {
  const cols = [
    { label: "Nuovo", color: "#52525B", items: ["Ferramenta Blu"] },
    { label: "Contattato", color: "#0A192F", items: ["Studio Verdi"] },
    { label: "Trattativa", color: "#B23E00", items: ["Bar Centrale", "Hotel Adria"] },
    { label: "Vinto", color: "#059669", items: ["Pasticceria Neri"] },
  ];
  return (
    <MockupFrame>
      <div className="grid grid-cols-4 gap-1.5">
        {cols.map((c) => (
          <div key={c.label} className="min-w-0">
            <div className="text-[6.5px] font-mono uppercase tracking-wide mb-1 truncate" style={{ color: c.color }}>{c.label}</div>
            <div className="space-y-1">
              {c.items.map((it) => (
                <div key={it} className="bg-white border border-[#E4E4E1] rounded p-1.5 text-[7.5px] font-medium leading-tight">{it}</div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </MockupFrame>
  );
}

export function AgendaVisual() {
  const days = ["LUN", "MAR", "MER", "GIO", "VEN"];
  const appts = { 0: ["10:00 Studio Verdi"], 2: ["11:30 Bianchi"], 4: ["15:00 Caffè Aurora"] };
  return (
    <MockupFrame>
      <div className="grid grid-cols-5 gap-1">
        {days.map((d, i) => (
          <div key={d} className={`bg-white border rounded p-1 min-h-[100px] ${i === 2 ? "border-[#B23E00]" : "border-[#E4E4E1]"}`}>
            <div className="text-[6px] font-mono text-[#6B6B72] text-center">{d}</div>
            <div className="text-[10px] font-cabinet font-black text-center mb-1">{22 + i}</div>
            {(appts[i] || []).map((a) => (
              <div key={a} className="bg-[#0A192F0D] border-l-2 border-[#B23E00] rounded-sm px-1 py-0.5 text-[6px] mb-0.5 leading-tight">{a}</div>
            ))}
          </div>
        ))}
      </div>
    </MockupFrame>
  );
}

export function OrdiniVisual() {
  const orders = [
    ["ORD-0041", "Rossi Spa", "€1.240", "Confermato", "#0A192F"],
    ["ORD-0040", "Bianchi Tessuti", "€860", "In evasione", "#B45309"],
    ["ORD-0039", "Caffè Aurora", "€2.100", "Spedito", "#0EA5E9"],
  ];
  return (
    <MockupFrame>
      <div className="space-y-2">
        {orders.map(([num, client, total, status, color]) => (
          <div key={num} className="bg-white border border-[#E4E4E1] rounded-md p-2.5">
            <div className="flex items-center justify-between mb-1">
              <span className="font-mono text-[8px] text-[#6B6B72]">{num}</span>
              <span className="font-cabinet font-black text-[11px]">{total}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-medium truncate">{client}</span>
              <span className="text-[7px] font-mono uppercase px-1.5 py-0.5 rounded shrink-0" style={{ background: `${color}15`, color }}>{status}</span>
            </div>
          </div>
        ))}
      </div>
    </MockupFrame>
  );
}

export function ProvvigioniVisual() {
  const tiers = [
    { threshold: "€2.000", bonus: "€500", reached: true },
    { threshold: "€3.000", bonus: "€360", reached: true },
    { threshold: "€5.000", bonus: "€600", reached: false },
  ];
  return (
    <MockupFrame>
      <div className="bg-white border border-[#E4E4E1] rounded-md p-2.5 mb-2.5 text-center">
        <div className="font-mono text-[8px] uppercase tracking-widest text-[#6B6B72]">Provvigioni maturate</div>
        <div className="font-cabinet font-black text-xl text-[#059669]">€1.240</div>
      </div>
      <div className="bg-white border border-[#E4E4E1] rounded-md p-2.5">
        <div className="font-mono text-[7px] uppercase tracking-widest text-[#52525B] mb-1.5">Scala premi</div>
        <div className="space-y-1">
          {tiers.map((t) => (
            <div key={t.threshold} className="flex items-center justify-between">
              <span className={`text-[9px] ${t.reached ? "text-[#0A0A0A] font-medium" : "text-[#6B6B72]"}`}>{t.threshold}</span>
              <span className={`text-[9px] font-mono ${t.reached ? "text-[#059669]" : "text-[#6B6B72]"}`}>{t.reached ? "✓ " : ""}{t.bonus}</span>
            </div>
          ))}
        </div>
      </div>
    </MockupFrame>
  );
}

export function AutomazioniVisual() {
  const rules = [
    ["Cliente senza ordini da 90gg", "Crea promemoria"],
    ["Offerta in scadenza", "Invia email"],
    ["Compleanno cliente", "Invia promemoria"],
  ];
  return (
    <MockupFrame>
      <div className="space-y-2">
        {rules.map(([trig, act]) => (
          <div key={trig} className="bg-white border border-[#E4E4E1] rounded-md p-2.5 flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-[#B23E00] flex items-center justify-center shrink-0">
              <Zap className="w-3 h-3 text-white" />
            </div>
            <div className="min-w-0">
              <div className="text-[9px] text-[#52525B] truncate"><span className="font-mono uppercase text-[7px] text-[#B23E00]">Quando</span> {trig}</div>
              <div className="text-[9px] text-[#0A0A0A] font-medium truncate"><span className="font-mono uppercase text-[7px] text-[#0A192F]">Allora</span> {act}</div>
            </div>
          </div>
        ))}
      </div>
    </MockupFrame>
  );
}

export function AIVisual() {
  return (
    <MockupFrame>
      <div className="space-y-2.5">
        <div className="flex gap-2 flex-row-reverse">
          <div className="w-5 h-5 rounded bg-[#0A192F] flex items-center justify-center shrink-0 text-white text-[7px] font-bold">TU</div>
          <div className="bg-[#0A192F] text-white rounded-md p-2 text-[10px] max-w-[75%]">Aggiungi una visita da Rossi Spa domani alle 10</div>
        </div>
        <div className="flex gap-2">
          <div className="w-5 h-5 rounded bg-[#B23E00] flex items-center justify-center shrink-0"><Sparkles className="w-2.5 h-2.5 text-white" /></div>
          <div className="bg-white border border-[#E4E4E1] rounded-md p-2 text-[10px] max-w-[75%]">Fatto! Ho creato l'appuntamento con Rossi Spa domani alle 10:00. ✓</div>
        </div>
      </div>
    </MockupFrame>
  );
}

export function GiroVisiteVisual() {
  const stops = ["Rossi Spa", "Bianchi Tessuti", "Caffè Aurora"];
  return (
    <MockupFrame>
      <div className="relative bg-[#E8ECF0] rounded-md h-24 mb-2.5 overflow-hidden">
        <svg viewBox="0 0 200 90" className="w-full h-full">
          <path d="M20,70 Q60,20 100,45 T180,20" fill="none" stroke="#B23E00" strokeWidth="2" strokeDasharray="4 3" />
          {[[20, 70], [100, 45], [180, 20]].map(([x, y], i) => (
            <g key={i}>
              <circle cx={x} cy={y} r="7" fill="#0A192F" />
              <text x={x} y={y + 3} fontSize="8" fill="white" textAnchor="middle" fontWeight="bold">{i + 1}</text>
            </g>
          ))}
        </svg>
      </div>
      <div className="space-y-1.5">
        {stops.map((s, i) => (
          <div key={s} className="flex items-center gap-2 bg-white border border-[#E4E4E1] rounded-md p-1.5">
            <div className="w-4 h-4 rounded-full bg-[#0A192F] text-white flex items-center justify-center text-[8px] font-bold shrink-0">{i + 1}</div>
            <div className="text-[9px] font-medium truncate">{s}</div>
          </div>
        ))}
      </div>
    </MockupFrame>
  );
}

export function GDPRVisual() {
  return (
    <MockupFrame>
      <div className="space-y-2.5">
        <div className="bg-white border border-[#E4E4E1] rounded-md p-2.5 flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-md bg-[#F3F3F1] flex items-center justify-center shrink-0">
            <Download className="w-3.5 h-3.5 text-[#0A192F]" />
          </div>
          <div className="text-[10px] font-medium">Scarica i tuoi dati</div>
        </div>
        <div className="bg-[#FEF2F2] border border-[#DC262630] rounded-md p-2.5 flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-md bg-white flex items-center justify-center shrink-0">
            <Trash2 className="w-3.5 h-3.5 text-[#DC2626]" />
          </div>
          <div className="text-[10px] font-medium text-[#DC2626]">Elimina account definitivamente</div>
        </div>
        <div className="flex items-center gap-1.5 text-[8px] text-[#6B6B72] justify-center pt-1">
          <ShieldCheck className="w-3 h-3" /> Conforme GDPR
        </div>
      </div>
    </MockupFrame>
  );
}
