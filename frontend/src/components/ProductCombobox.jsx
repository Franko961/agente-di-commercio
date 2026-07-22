import { useState } from "react";
import { Check, ChevronsUpDown } from "lucide-react";
import { Popover, PopoverTrigger, PopoverContent } from "./ui/popover";
import { Command, CommandInput, CommandList, CommandEmpty, CommandGroup, CommandItem } from "./ui/command";

// Selettore prodotto con ricerca (nome o SKU). Sostituisce la <select> nativa,
// diventata inutilizzabile con listini da centinaia di prodotti (es. import
// massivo PagineSì). Usato sia in Ordini.jsx che in Offers.jsx.
export default function ProductCombobox({ products, value, onSelect, className = "" }) {
  const [open, setOpen] = useState(false);
  const selected = products.find((p) => p.id === value);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          className={`flex items-center justify-between gap-1 bg-white border border-[#E4E4E1] rounded-md px-2 py-1.5 text-[12px] text-left ${
            selected ? "text-[#0A192F]" : "text-[#A1A1AA]"
          } ${className}`}
        >
          <span className="truncate">{selected ? selected.name : "prodotto"}</span>
          <ChevronsUpDown className="h-3.5 w-3.5 shrink-0 opacity-40" />
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-[300px] p-0" align="start">
        <Command>
          <CommandInput placeholder="Cerca per nome o codice..." className="text-[12px]" />
          <CommandList>
            <CommandEmpty className="py-4 text-center text-[12px] text-[#71717A]">
              Nessun prodotto trovato
            </CommandEmpty>
            <CommandGroup>
              {products.map((p) => (
                <CommandItem
                  key={p.id}
                  value={p.id}
                  keywords={[p.name, p.sku || ""].filter(Boolean)}
                  onSelect={() => {
                    onSelect(p);
                    setOpen(false);
                  }}
                  className="text-[12px] cursor-pointer"
                >
                  <Check className={`mr-2 h-3.5 w-3.5 shrink-0 ${value === p.id ? "opacity-100" : "opacity-0"}`} />
                  <div className="flex flex-col overflow-hidden">
                    <span className="truncate">{p.name}</span>
                    {p.sku ? <span className="text-[10px] text-[#A1A1AA] font-mono">{p.sku}</span> : null}
                  </div>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
