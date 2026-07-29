import { useState } from "react";
import {
  Rocket, Users, KanbanSquare, CalendarDays, ShoppingCart, Coins,
  Sparkles, Zap, Navigation, ShieldCheck, ChevronDown, HelpCircle,
} from "lucide-react";
import { HELP_CATEGORIES } from "@/content/help";
import {
  IniziareVisual, ClientiVisual, LeadVisual, AgendaVisual, OrdiniVisual,
  ProvvigioniVisual, AIVisual, AutomazioniVisual, GiroVisiteVisual, GDPRVisual,
} from "@/components/AppVisuals";

const ICONS = { Rocket, Users, KanbanSquare, CalendarDays, ShoppingCart, Coins, Sparkles, Zap, Navigation, ShieldCheck };

// Una ricostruzione stilizzata per categoria (stesse componenti condivise
// col tour guidato pubblico, vedi components/AppVisuals.jsx), per non far
// sembrare la pagina solo un elenco di testo.
const VISUALS = {
  iniziare: IniziareVisual,
  clienti: ClientiVisual,
  lead: LeadVisual,
  agenda: AgendaVisual,
  ordini: OrdiniVisual,
  provvigioni: ProvvigioniVisual,
  ai: AIVisual,
  automazioni: AutomazioniVisual,
  "giro-visite": GiroVisiteVisual,
  gdpr: GDPRVisual,
};

function CategorySection({ category, open, onToggle }) {
  const Icon = ICONS[category.icon] || HelpCircle;
  const Visual = VISUALS[category.id];
  return (
    <div className="bg-white border border-[#E4E4E1] rounded-lg overflow-hidden">
      <button
        onClick={onToggle}
        data-testid={`help-category-${category.id}`}
        className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-[#F9F9F8] transition-colors"
      >
        <div className="w-9 h-9 rounded-md bg-[#F3F3F1] flex items-center justify-center shrink-0">
          <Icon className="w-4 h-4 text-[#0A192F]" strokeWidth={1.75} />
        </div>
        <span className="font-cabinet font-bold text-[15px] flex-1">{category.label}</span>
        <ChevronDown className={`w-4 h-4 text-[#A1A1AA] shrink-0 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <div className="px-5 pb-6 border-t border-[#E4E4E1] pt-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
            {Visual && (
              <div className="order-2 md:order-1">
                <Visual />
              </div>
            )}
            <div className={`order-1 ${Visual ? "md:order-2" : ""} space-y-4`}>
              {category.articles.map((a) => (
                <div key={a.title}>
                  <div className="font-cabinet font-bold text-[13px] mb-1.5">{a.title}</div>
                  <p className="text-[13px] text-[#52525B] leading-relaxed">{a.body}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function HelpCenter() {
  const [openId, setOpenId] = useState(HELP_CATEGORIES[0]?.id || null);

  return (
    <div className="p-4 md:p-8 max-w-4xl mx-auto">
      <meta name="robots" content="noindex, nofollow" />

      <div className="mb-8">
        <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#FF5A00] mb-2">Aiuto</div>
        <h1 className="font-cabinet font-black text-3xl md:text-4xl tracking-tight mb-2">Centro assistenza</h1>
        <p className="text-[14px] text-[#52525B]">
          Risposte rapide, organizzate per argomento — ogni articolo si legge in meno di un minuto.
        </p>
      </div>

      <div className="space-y-3">
        {HELP_CATEGORIES.map((cat) => (
          <CategorySection
            key={cat.id}
            category={cat}
            open={openId === cat.id}
            onToggle={() => setOpenId(openId === cat.id ? null : cat.id)}
          />
        ))}
      </div>
    </div>
  );
}
