import { useEffect, useState } from "react";
import { Loader2, Save, Home, Building2 } from "lucide-react";
import { toast } from "sonner";
import { getAddresses, updateAddresses } from "../../api/settings";
import LocationPicker from "../LocationPicker";

export default function PercorsiTab() {
  const [addresses, setAddresses] = useState(null); // null = caricamento
  const [addressesBusy, setAddressesBusy] = useState(false);

  const loadAddresses = async () => {
    try {
      setAddresses(await getAddresses());
    } catch {
      toast.error("Impossibile caricare gli indirizzi");
    }
  };

  const saveAddresses = async (e) => {
    e.preventDefault();
    setAddressesBusy(true);
    try {
      setAddresses(await updateAddresses(addresses));
      toast.success("Indirizzi aggiornati");
    } catch {
      toast.error("Errore nel salvataggio degli indirizzi");
    } finally {
      setAddressesBusy(false);
    }
  };

  useEffect(() => {
    loadAddresses();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <>
      <div className="mb-8">
        <div className="font-mono text-[11px] uppercase tracking-widest text-[#B23E00] mb-1">Impostazioni</div>
        <h1 className="font-cabinet text-3xl font-black">Punti di partenza</h1>
        <p className="text-[#52525B] mt-1">
          Imposta l'indirizzo di casa e/o ufficio per poterli scegliere come punto di partenza nel pianificatore del giro visite (Mappa clienti).
        </p>
      </div>

      {addresses === null ? (
        <div className="flex items-center gap-2 text-[13px] text-[#6B6B72]">
          <Loader2 className="w-4 h-4 animate-spin" /> Caricamento…
        </div>
      ) : (
        <form onSubmit={saveAddresses} className="space-y-5">
          <div className="border border-[#E4E4E1] rounded-lg p-5">
            <div className="flex items-center gap-2 mb-3">
              <Home className="w-4 h-4 text-[#B23E00]" />
              <div className="font-semibold text-[15px]">Casa</div>
            </div>
            <input
              value={addresses.home_address || ""}
              onChange={(e) => setAddresses({ ...addresses, home_address: e.target.value })}
              placeholder="Etichetta o indirizzo (es. Via Roma 10, Bologna)"
              className="w-full mb-3 px-3 py-2 border border-[#E4E4E1] rounded-md text-[13px]"
            />
            <LocationPicker
              address={addresses.home_address} city="" province=""
              lat={addresses.home_lat} lng={addresses.home_lng}
              onChange={(lat, lng) => setAddresses((prev) => ({ ...prev, home_lat: lat, home_lng: lng }))}
            />
          </div>

          <div className="border border-[#E4E4E1] rounded-lg p-5">
            <div className="flex items-center gap-2 mb-3">
              <Building2 className="w-4 h-4 text-[#B23E00]" />
              <div className="font-semibold text-[15px]">Ufficio</div>
            </div>
            <input
              value={addresses.office_address || ""}
              onChange={(e) => setAddresses({ ...addresses, office_address: e.target.value })}
              placeholder="Etichetta o indirizzo (es. Via Milano 5, Bologna)"
              className="w-full mb-3 px-3 py-2 border border-[#E4E4E1] rounded-md text-[13px]"
            />
            <LocationPicker
              address={addresses.office_address} city="" province=""
              lat={addresses.office_lat} lng={addresses.office_lng}
              onChange={(lat, lng) => setAddresses((prev) => ({ ...prev, office_lat: lat, office_lng: lng }))}
            />
          </div>

          <button
            type="submit"
            disabled={addressesBusy}
            className="flex items-center gap-1.5 px-4 py-2 bg-[#B23E00] hover:bg-[#E04F00] text-white rounded-md text-[13px] font-medium transition-colors disabled:opacity-50"
          >
            <Save className="w-3.5 h-3.5" /> {addressesBusy ? "Salvataggio…" : "Salva indirizzi"}
          </button>
        </form>
      )}
    </>
  );
}
