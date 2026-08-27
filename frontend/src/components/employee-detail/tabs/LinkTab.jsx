import { QRCodeSVG } from "qrcode.react";
import { RefreshCw, Power, PowerOff, Copy } from "lucide-react";

export default function LinkTab({ employee, newLink, onRegenerate, onToggleActive, onCopy, newPin, onRegeneratePin }) {
  const url = newLink ? `${window.location.origin}/richiedi-assenza/${newLink.token}` : null;
  return (
    <div className="space-y-4">
      <div className="bg-white border border-[#E4E4E1] rounded-md p-4 space-y-2 text-[13px]">
        <div className="flex justify-between"><span className="text-[#6B6B72]">Stato</span><span className="font-medium">{employee.active ? "Attivo" : "Disattivato"}</span></div>
        <div className="flex justify-between"><span className="text-[#6B6B72]">Ultimo utilizzo</span><span className="font-medium">{employee.last_used_at ? new Date(employee.last_used_at).toLocaleString("it-IT") : "Mai"}</span></div>
      </div>
      <div className="flex gap-2">
        <button onClick={onRegenerate} className="flex-1 flex items-center justify-center gap-2 px-3 py-2.5 border border-[#E4E4E1] rounded-md text-[13px] font-medium hover:border-[#B23E00]">
          <RefreshCw className="w-4 h-4" /> Rigenera
        </button>
        <button onClick={onToggleActive} className="flex-1 flex items-center justify-center gap-2 px-3 py-2.5 border border-[#E4E4E1] rounded-md text-[13px] font-medium hover:border-[#0A192F]">
          {employee.active ? <PowerOff className="w-4 h-4" /> : <Power className="w-4 h-4" />} {employee.active ? "Disattiva" : "Riattiva"}
        </button>
      </div>
      {newLink && (
        <div className="bg-[#F9F9F8] border border-[#E4E4E1] rounded-md p-4 space-y-3">
          <p className="text-[12px] text-[#52525B]">Nuovo link generato: copialo ora, non verrà più mostrato.</p>
          <div className="flex justify-center bg-white p-3 rounded-md border border-[#E4E4E1]">
            <QRCodeSVG value={url} size={140} />
          </div>
          <code className="block text-[11px] break-all text-[#52525B]">{url}</code>
          <button onClick={() => onCopy(newLink.token)} className="w-full flex items-center justify-center gap-2 bg-[#0A192F] text-white py-2 rounded-md text-[12px] font-medium">
            <Copy className="w-3.5 h-3.5" /> Copia link
          </button>
        </div>
      )}

      <div className="bg-white border border-[#E4E4E1] rounded-md p-4 space-y-3">
        <div className="font-mono text-[10px] uppercase tracking-widest text-[#6B6B72]">PIN chiosco presenze</div>
        <p className="text-[12px] text-[#52525B]">
          Usato per identificarsi al QR di timbratura affisso in azienda (Personale → QR Timbratura).{" "}
          {employee.has_pin ? "PIN già impostato." : "Nessun PIN impostato: il dipendente non può ancora timbrare al chiosco."}
        </p>
        <button onClick={onRegeneratePin} className="w-full flex items-center justify-center gap-2 px-3 py-2 border border-[#E4E4E1] rounded-md text-[13px] font-medium hover:border-[#B23E00]">
          <RefreshCw className="w-4 h-4" /> {employee.has_pin ? "Rigenera PIN" : "Genera PIN"}
        </button>
        {newPin && (
          <div className="bg-[#F9F9F8] border border-[#E4E4E1] rounded-md p-4 text-center">
            <p className="text-[12px] text-[#52525B] mb-2">Nuovo PIN generato: comunicalo ora al dipendente, non verrà più mostrato.</p>
            <div className="font-cabinet font-black text-3xl tracking-[0.3em]">{newPin.pin}</div>
          </div>
        )}
      </div>
    </div>
  );
}
