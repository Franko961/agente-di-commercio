export default function MezzoTab({ vehicle, nextRevisione }) {
  if (!vehicle) {
    return <div className="bg-white border border-[#E4E4E1] rounded-md p-6 text-center text-[#6B6B72] text-[13px]">Nessun mezzo assegnato (o modulo Flotta non attivo).</div>;
  }
  return (
    <div className="space-y-2">
      <div className="bg-white border border-[#E4E4E1] rounded-md p-4">
        <div className="font-cabinet font-bold text-[16px]">{vehicle.plate}</div>
        <div className="text-[13px] text-[#52525B] mt-1">{vehicle.model || "—"}</div>
        {vehicle.current_km != null && <div className="text-[13px] text-[#52525B] mt-1">Km attuali: {vehicle.current_km.toLocaleString("it-IT")}</div>}
        {nextRevisione ? (
          <div className="text-[13px] text-[#52525B] mt-1">Prossima revisione: {nextRevisione.due_date}</div>
        ) : (
          <div className="text-[13px] text-[#6B6B72] mt-1">Nessuna revisione in programma</div>
        )}
      </div>
    </div>
  );
}
