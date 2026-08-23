import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { CheckCircle2, ChevronLeft, Timer, User } from "lucide-react";
import { toast } from "sonner";
import api from "../api";
import PageMeta from "../components/PageMeta";

// Pagina pubblica del "chiosco" di timbratura: raggiunta da un QR fisico
// UGUALE per tutti i dipendenti di un'azienda, pensato per essere affisso
// all'ingresso — a differenza del link personale (/richiedi-assenza/:token,
// usato per ferie/permessi), qui il token identifica solo l'AZIENDA, non un
// singolo dipendente: chi timbra sceglie il proprio nome da un elenco e
// conferma con un PIN a 4 cifre (vedi attendance_service sul backend per il
// perché — evita che un collega timbri al posto di un altro avendo solo
// accesso fisico al QR). Nessuna posizione GPS. Non in pageMeta.js/sitemap,
// noindex, stesso principio di RichiediAssenza.jsx.
export default function Timbra() {
  const { token } = useParams();
  const [employees, setEmployees] = useState(null); // null = caricamento, false = QR non valido
  const [selected, setSelected] = useState(null); // { id, name, clocked_in }
  const [pin, setPin] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [done, setDone] = useState(null); // { name, clocked_in } dopo la timbratura

  const loadEmployees = () => {
    api.get(`/attendance/kiosk/${token}/employees`)
      .then(({ data }) => setEmployees(data))
      .catch(() => setEmployees(false));
  };
  useEffect(() => { loadEmployees(); }, [token]); // eslint-disable-line react-hooks/exhaustive-deps

  const selectEmployee = (emp) => {
    setSelected(emp);
    setPin("");
    setError(null);
  };

  const backToList = () => {
    setSelected(null);
    setPin("");
    setError(null);
    setDone(null);
    loadEmployees();
  };

  const submit = async (e) => {
    e.preventDefault();
    if (pin.length !== 4) return;
    setBusy(true);
    setError(null);
    try {
      const action = selected.clocked_in ? "clock-out" : "clock-in";
      await api.post(`/attendance/kiosk/${token}/${action}`, { employee_id: selected.id, pin });
      setDone({ name: selected.name, clocked_in: !selected.clocked_in });
      toast.success(selected.clocked_in ? "Uscita registrata" : "Ingresso registrato");
    } catch (err) {
      setError(err?.response?.data?.detail || "Timbratura non riuscita, riprova.");
      setPin("");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F9F9F8] flex flex-col">
      <PageMeta path="/timbra" title="Timbratura — SALESFLY" description="Chiosco di timbratura ingresso/uscita." noindex />

      <header className="border-b border-[#E4E4E1] bg-white px-6 py-4 flex items-center justify-center">
        <Link to="/" className="flex items-center gap-2">
          <div className="w-9 h-9 flex items-center justify-center shrink-0">
            <img src="/logo-mark.png" alt="SALESFLY" className="w-full h-full object-contain" />
          </div>
          <span className="font-cabinet font-black text-lg">SALESFLY.</span>
        </Link>
      </header>

      <main className="flex-1 px-6 py-16 max-w-md mx-auto w-full">
        {employees === null && (
          <p className="text-center text-[#6B6B72] text-[14px]">Caricamento…</p>
        )}

        {employees === false && (
          <div className="bg-white border border-[#E4E4E1] rounded-xl p-8 text-center">
            <h1 className="font-cabinet font-black text-2xl mb-2">QR non valido</h1>
            <p className="text-[#52525B] text-sm">
              Questo QR non è (più) valido. Chiedi a chi gestisce il personale della tua azienda di generarne uno nuovo.
            </p>
          </div>
        )}

        {employees && done && (
          <div className="bg-white border border-[#E4E4E1] rounded-xl p-8 text-center">
            <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-4" />
            <h1 className="font-cabinet font-black text-2xl mb-2">
              {done.clocked_in ? "Ingresso registrato" : "Uscita registrata"}
            </h1>
            <p className="text-[#52525B] text-sm mb-6">Ciao {done.name.split(" ")[0]}, buon lavoro.</p>
            <button onClick={backToList} className="w-full bg-[#0A192F] text-white rounded-md py-2.5 text-sm font-medium">
              Fatto
            </button>
          </div>
        )}

        {employees && employees.length > 0 && !selected && !done && (
          <>
            <div className="text-center mb-6">
              <Timer className="w-8 h-8 text-[#6B6B72] mx-auto mb-2" />
              <h1 className="font-cabinet font-black text-2xl mb-1">Chi sei?</h1>
              <p className="text-[#52525B] text-sm">Tocca il tuo nome per timbrare.</p>
            </div>
            <div className="space-y-2">
              {employees.map((emp) => (
                <button key={emp.id} onClick={() => selectEmployee(emp)}
                  className="w-full flex items-center justify-between gap-3 bg-white border border-[#E4E4E1] rounded-xl p-4 text-left hover:border-[#B23E00]">
                  <span className="flex items-center gap-3">
                    <User className="w-4 h-4 text-[#6B6B72]" />
                    <span className="font-medium text-[15px]">{emp.name}</span>
                  </span>
                  {emp.clocked_in && (
                    <span className="font-mono text-[10px] uppercase tracking-widest px-1.5 py-0.5 rounded-full bg-[#05966920] text-[#059669]">In servizio</span>
                  )}
                </button>
              ))}
            </div>
          </>
        )}

        {employees && employees.length === 0 && !done && (
          <div className="bg-white border border-[#E4E4E1] rounded-xl p-8 text-center">
            <p className="text-[#52525B] text-sm">Nessun dipendente disponibile per la timbratura.</p>
          </div>
        )}

        {selected && !done && (
          <div className="bg-white border border-[#E4E4E1] rounded-xl p-8">
            <button onClick={backToList} className="flex items-center gap-1 text-[13px] text-[#52525B] mb-4 hover:text-[#0A192F]">
              <ChevronLeft className="w-4 h-4" /> Non sono io
            </button>
            <div className="text-center mb-6">
              <h1 className="font-cabinet font-black text-2xl mb-1">Ciao {selected.name.split(" ")[0]}.</h1>
              <p className="text-[#52525B] text-sm">Inserisci il tuo PIN per {selected.clocked_in ? "timbrare l'uscita" : "timbrare l'ingresso"}.</p>
            </div>
            <form onSubmit={submit} className="space-y-4">
              <input
                type="password" inputMode="numeric" pattern="[0-9]*" maxLength={4} autoFocus
                value={pin} onChange={(e) => setPin(e.target.value.replace(/\D/g, "").slice(0, 4))}
                className="w-full text-center text-3xl tracking-[0.5em] border border-[#E4E4E1] rounded-md py-3 font-cabinet font-bold"
                placeholder="••••"
              />
              {error && <p className="text-center text-[13px] text-red-600">{error}</p>}
              <button type="submit" disabled={busy || pin.length !== 4}
                className={`w-full py-2.5 rounded-md text-sm font-medium disabled:opacity-60 ${
                  selected.clocked_in ? "bg-[#DC2626] text-white" : "bg-[#0A192F] text-white"
                }`}>
                {busy ? "Attendere…" : selected.clocked_in ? "Timbra uscita" : "Timbra ingresso"}
              </button>
            </form>
          </div>
        )}
      </main>
    </div>
  );
}
