import { Search, ShoppingCart } from "lucide-react";
import { fmt } from "./constants";

export default function ClientList({ filteredClients, query, setQuery, ordersForClient, pendingOffersForClient, onSelectClient }) {
  return (
    <>
      <div className="relative mb-4">
        <Search className="w-4 h-4 text-[#6B6B72] absolute left-3 top-1/2 -translate-y-1/2" />
        <input
          data-testid="orders-client-search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Cerca cliente per nome, referente o città…"
          className="w-full bg-white border border-[#E4E4E1] rounded-md pl-9 pr-3 py-2.5 text-[13px] focus:outline-none focus:border-[#0A192F]"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {filteredClients.map((c) => {
          const clientOrders = ordersForClient(c.id);
          const pendingCount = pendingOffersForClient(c.id).length;
          const totale = clientOrders.reduce((s, o) => s + (o.total || 0), 0);
          return (
            <button
              key={c.id}
              data-testid={`orders-client-card-${c.id}`}
              onClick={() => onSelectClient(c)}
              className="text-left bg-white border border-[#E4E4E1] hover:border-[#0A192F] rounded-md p-4 transition-colors relative"
            >
              {pendingCount > 0 && (
                <span className="absolute -top-2 -right-2 bg-[#B23E00] text-white text-[10px] font-mono font-bold w-5 h-5 rounded-full flex items-center justify-center">
                  {pendingCount}
                </span>
              )}
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="font-cabinet font-bold text-[15px] truncate">{c.company_name}</div>
                  <div className="text-[12px] text-[#52525B] truncate">{c.contact_name || c.city || "—"}</div>
                </div>
                <ShoppingCart className="w-4 h-4 text-[#6B6B72] shrink-0" />
              </div>
              <div className="flex items-center justify-between mt-3 pt-3 border-t border-[#E4E4E1]">
                <span className="font-mono text-[10px] uppercase tracking-widest text-[#6B6B72]">
                  {clientOrders.length} {clientOrders.length === 1 ? "ordine" : "ordini"}
                </span>
                <span className="font-cabinet font-bold text-[14px]">{fmt(totale)}</span>
              </div>
            </button>
          );
        })}
      </div>
      {filteredClients.length === 0 && (
        <div className="bg-white border border-[#E4E4E1] rounded-md p-8 text-center text-[#6B6B72] text-[13px]">
          Nessun cliente trovato.
        </div>
      )}
    </>
  );
}
