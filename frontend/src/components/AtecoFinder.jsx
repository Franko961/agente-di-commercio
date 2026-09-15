import { useState } from "react";
import { Search, Check, ChevronsUpDown, AlertTriangle, FileSearch } from "lucide-react";
import { Popover, PopoverTrigger, PopoverContent } from "@/components/ui/popover";
import { Command, CommandInput, CommandList, CommandEmpty, CommandGroup, CommandItem } from "@/components/ui/command";
import CalculatorCTA from "@/components/CalculatorCTA";

// Elenco costruito solo con codici verificati via ricerca (fonti ufficiali/
// specializzate, vedi content/blog/articles/codice-ateco-agente-di-commercio.js
// per il ragionamento generale sui gruppi 46.1x) — nessun codice a 6 cifre
// "indovinato": dove non avevamo una fonte specifica per un settore, non è
// stato aggiunto come voce a sé, per non dare un falso senso di precisione.
// "nota" è mostrata solo per le voci che si comportano in modo sorprendente
// (le due eccezioni fuori dal gruppo 46.1, e il codice generico "misto").
const ATECO_SETTORI = [
  { settore: "Auto e veicoli leggeri", codice: "45.11.02", nota: "Eccezione: non rientra nel gruppo 46.1 — è una divisione a parte dedicata al commercio di autoveicoli." },
  { settore: "Energia elettrica e gas", codice: "35.14.00", nota: "Eccezione: non è commercio all'ingrosso — appartiene alla divisione 35, fornitura di energia." },
  { settore: "Materie prime agricole, animali vivi, materie tessili grezze", codice: "46.11" },
  { settore: "Combustibili, minerali, metalli, prodotti chimici", codice: "46.12" },
  { settore: "Materiali da costruzione, infissi, sanitari, vetro piano", codice: "46.13.02" },
  { settore: "Legname e altri materiali da costruzione", codice: "46.13.03" },
  { settore: "Macchine e impianti per industria e commercio", codice: "46.14.01" },
  { settore: "Macchine per costruzioni edili e stradali", codice: "46.14.02" },
  { settore: "Macchine per ufficio, informatica, telecomunicazioni", codice: "46.14.03" },
  { settore: "Macchine e attrezzature agricole, trattori", codice: "46.14.04" },
  { settore: "Navi, aeromobili e altri veicoli (non auto)", codice: "46.14.05" },
  { settore: "Mobili in legno, metallo e materie plastiche", codice: "46.15.01" },
  { settore: "Ferramenta e bricolage", codice: "46.15.02" },
  { settore: "Casalinghi, porcellane, vetro, riscaldamento e condizionamento domestico", codice: "46.15.03" },
  { settore: "Tessile, abbigliamento, pellicce, calzature, pelletteria", codice: "46.16.0" },
  { settore: "Ortofrutta fresca, congelata, surgelata", codice: "46.17.01" },
  { settore: "Carni e salumi", codice: "46.17.02" },
  { settore: "Latte, burro, formaggi", codice: "46.17.03" },
  { settore: "Oli e grassi alimentari", codice: "46.17.04" },
  { settore: "Bevande", codice: "46.17.05" },
  { settore: "Prodotti ittici", codice: "46.17.06" },
  { settore: "Altri alimentari, mangimi per animali, tabacco", codice: "46.17.07" },
  { settore: "Carta e cartone (esclusi imballaggi e cancelleria)", codice: "46.18.11" },
  { settore: "Libri e altre pubblicazioni", codice: "46.18.12" },
  { settore: "Computer, elettronica di consumo, materiale elettrico per uso domestico", codice: "46.18.21" },
  { settore: "Elettrodomestici", codice: "46.18.22" },
  { settore: "Prodotti farmaceutici, erboristeria per uso medico", codice: "46.18.31" },
  { settore: "Prodotti sanitari, medicali, chirurgici, ortopedici", codice: "46.18.32" },
  { settore: "Profumeria e cosmetica", codice: "46.18.33" },
  { settore: "Più settori diversi, senza prevalenza di alcuno", codice: "46.19.00", nota: "Il codice per chi rappresenta mandanti di settori diversi tra loro — tipico di un agente plurimandatario senza un settore prevalente." },
];

export default function AtecoFinder() {
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState(null);

  return (
    <div className="my-8 bg-white border border-[#E4E4E1] rounded-xl p-6">
      <div className="flex items-center gap-2 mb-5">
        <FileSearch className="w-4 h-4 text-[#B23E00]" />
        <div className="font-cabinet font-black text-[15px]">Trova il tuo codice ATECO</div>
      </div>

      <label className="block text-[12px] font-medium text-[#52525B] mb-1.5">
        Che prodotti rappresenti principalmente?
      </label>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <button
            type="button"
            data-testid="ateco-finder-trigger"
            className="w-full flex items-center justify-between gap-2 bg-white border border-[#E4E4E1] rounded-md px-3 py-2.5 text-[13px] text-left"
          >
            <span className={`truncate flex items-center gap-2 ${selected ? "text-[#0A0A0A]" : "text-[#6B6B72]"}`}>
              <Search className="w-3.5 h-3.5 shrink-0 opacity-50" />
              {selected ? selected.settore : "Cerca il tuo settore..."}
            </span>
            <ChevronsUpDown className="h-4 w-4 shrink-0 opacity-40" />
          </button>
        </PopoverTrigger>
        <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
          <Command>
            <CommandInput placeholder="Es. abbigliamento, alimentari, mobili..." className="text-[13px]" />
            <CommandList>
              <CommandEmpty className="py-4 text-center text-[12px] text-[#71717A]">
                Nessun settore trovato — vedi la nota sul codice generico qui sotto.
              </CommandEmpty>
              <CommandGroup>
                {ATECO_SETTORI.map((s) => (
                  <CommandItem
                    key={s.codice}
                    value={s.codice}
                    keywords={[s.settore]}
                    onSelect={() => {
                      setSelected(s);
                      setOpen(false);
                    }}
                    className="text-[13px] cursor-pointer"
                  >
                    <Check className={`mr-2 h-3.5 w-3.5 shrink-0 ${selected?.codice === s.codice ? "opacity-100" : "opacity-0"}`} />
                    <div className="flex flex-col overflow-hidden">
                      <span className="truncate">{s.settore}</span>
                      <span className="text-[10px] text-[#6B6B72] font-mono">{s.codice}</span>
                    </div>
                  </CommandItem>
                ))}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>

      {selected && (
        <div className="mt-5 pt-5 border-t border-[#E4E4E1]">
          <div className="text-[12px] text-[#52525B] mb-1">Codice ATECO</div>
          <div className="font-mono font-black text-[28px] text-[#0A192F] mb-2">{selected.codice}</div>
          <div className="text-[13px] text-[#3F3F46]">{selected.settore}</div>
          {selected.nota && (
            <div className="mt-4 flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-md p-3 text-[12px] text-amber-800">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{selected.nota}</span>
            </div>
          )}
        </div>
      )}

      <CalculatorCTA location="ateco_finder" />

      <p className="text-[11px] text-[#6B6B72] mt-4">
        Elenco indicativo dei codici principali, non esaustivo di tutti i sotto-codici possibili:
        conferma sempre il codice esatto con il commercialista al momento dell'iscrizione,
        soprattutto se rappresenti prodotti a cavallo tra due categorie.
      </p>
    </div>
  );
}
