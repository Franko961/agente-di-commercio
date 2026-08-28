import { useState } from "react";
import { QrCode, RefreshCw } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../ui/dialog";
import { getAttendanceKiosk, regenerateAttendanceKiosk } from "../../api/settings";

export default function KioskDialog() {
  const [kioskDialogOpen, setKioskDialogOpen] = useState(false);
  const [kioskHasToken, setKioskHasToken] = useState(null); // null = non ancora caricato
  const [kioskToken, setKioskToken] = useState(null); // token in chiaro, mostrato una sola volta dopo generazione

  const openKioskDialog = async () => {
    setKioskDialogOpen(true);
    if (kioskHasToken === null) {
      const data = await getAttendanceKiosk();
      setKioskHasToken(data.has_token);
    }
  };

  const regenerateKiosk = async () => {
    if (kioskHasToken && !window.confirm("Il QR attuale smetterà subito di funzionare. Rigenerare?")) return;
    const data = await regenerateAttendanceKiosk();
    setKioskToken(data.token);
    setKioskHasToken(true);
    toast.success("QR generato");
  };

  const kioskUrl = kioskToken ? `${window.location.origin}/timbra/${kioskToken}` : null;

  return (
    <>
      <button onClick={openKioskDialog} className="flex items-center gap-2 px-3 py-2.5 border border-[#E4E4E1] rounded-md text-[13px] font-medium hover:border-[#0A192F]">
        <QrCode className="w-4 h-4" /> QR Timbratura
      </button>

      <Dialog open={kioskDialogOpen} onOpenChange={(v) => { setKioskDialogOpen(v); if (!v) setKioskToken(null); }}>
        <DialogContent>
          <DialogHeader><DialogTitle>QR per la timbratura</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <p className="text-[13px] text-[#52525B]">
              Un unico QR per tutti i dipendenti, da stampare e affiggere all'ingresso: chi lo scansiona sceglie il proprio
              nome e inserisce il proprio PIN (impostabile dalla scheda di ciascun dipendente, tab Link) per timbrare
              ingresso/uscita. Nessuna posizione GPS: solo l'orario, registrato quando si scansiona il QR fisico.
            </p>
            {kioskToken ? (
              <div className="bg-[#F9F9F8] border border-[#E4E4E1] rounded-md p-4 space-y-3">
                <p className="text-[12px] text-[#52525B]">Nuovo QR generato: stampalo ora, non verrà più mostrato.</p>
                <div className="flex justify-center bg-white p-3 rounded-md border border-[#E4E4E1]">
                  <QRCodeSVG value={kioskUrl} size={180} />
                </div>
                <code className="block text-[11px] break-all text-[#52525B]">{kioskUrl}</code>
              </div>
            ) : kioskHasToken ? (
              <p className="text-[13px] text-[#52525B]">Un QR è già configurato. Rigeneralo solo se quello affisso è stato smarrito o va sostituito: quello attuale smetterà subito di funzionare.</p>
            ) : kioskHasToken === false ? (
              <p className="text-[13px] text-[#52525B]">Nessun QR generato finora.</p>
            ) : (
              <p className="text-[13px] text-[#6B6B72]">Caricamento…</p>
            )}
            {kioskHasToken !== null && (
              <button onClick={regenerateKiosk} className="w-full flex items-center justify-center gap-2 bg-[#0A192F] text-white py-2.5 rounded-md text-[13px] font-medium">
                <RefreshCw className="w-4 h-4" /> {kioskHasToken ? "Rigenera QR" : "Genera QR"}
              </button>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
