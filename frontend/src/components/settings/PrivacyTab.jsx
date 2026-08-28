import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2, Download, Trash2, AlertTriangle, Eye, EyeOff, Cookie } from "lucide-react";
import { toast } from "sonner";
import { exportMyData as exportMyDataApi, deleteMyAccount as deleteMyAccountApi } from "../../api/privacy";
import { useAuth } from "../../contexts/AuthContext";
import { useCookieConsent } from "../../contexts/CookieConsentContext";

export default function PrivacyTab() {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const { consent, openPreferences } = useCookieConsent();

  const [exporting, setExporting] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deletePassword, setDeletePassword] = useState("");
  const [deletePasswordVisible, setDeletePasswordVisible] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState("");
  const [deleting, setDeleting] = useState(false);

  const exportMyData = async () => {
    setExporting(true);
    try {
      const res = await exportMyDataApi();
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = "i-miei-dati-salesfly.zip";
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success("Download avviato");
    } catch {
      toast.error("Errore durante l'esportazione dei dati");
    } finally {
      setExporting(false);
    }
  };

  const deleteMyAccount = async () => {
    setDeleting(true);
    try {
      await deleteMyAccountApi(deletePassword);
      toast.success("Account eliminato definitivamente");
      await logout();
      navigate("/");
    } catch (err) {
      const msg = err?.response?.data?.detail || "Password non corretta, o errore durante l'eliminazione";
      toast.error(msg);
      setDeleting(false);
    }
  };

  return (
    <>
      <div className="mb-8">
        <div className="font-mono text-[11px] uppercase tracking-widest text-[#B23E00] mb-1">Impostazioni</div>
        <h1 className="font-cabinet text-3xl font-black">Privacy e dati</h1>
        <p className="text-[#52525B] mt-1">
          Gestisci i tuoi dati personali secondo il GDPR: puoi scaricarne una copia completa o richiederne la cancellazione definitiva.
        </p>
      </div>

      <div className="border border-[#E4E4E1] rounded-lg p-5 mb-5">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-md bg-[#F3F3F1] flex items-center justify-center shrink-0">
            <Download className="w-5 h-5 text-[#0A192F]" />
          </div>
          <div className="flex-1">
            <div className="font-semibold text-[15px]">Scarica i tuoi dati</div>
            <div className="text-[13px] text-[#52525B] mt-0.5">
              Un file .zip con tutti i tuoi dati (clienti, offerte, ordini, provvigioni, documenti, conversazioni con l'assistente AI e altro) in formato leggibile — il tuo diritto alla portabilità dei dati (art. 20 GDPR).
            </div>
            <button
              onClick={exportMyData}
              disabled={exporting}
              className="mt-3 flex items-center gap-1.5 px-4 py-2 bg-[#0A192F] hover:bg-[#172A45] text-white rounded-md text-[13px] font-medium transition-colors disabled:opacity-50"
            >
              {exporting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
              {exporting ? "Preparazione in corso…" : "Scarica i miei dati"}
            </button>
          </div>
        </div>
      </div>

      <div className="border border-[#E4E4E1] rounded-lg p-5 mb-5">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-md bg-[#F3F3F1] flex items-center justify-center shrink-0">
            <Cookie className="w-5 h-5 text-[#0A192F]" />
          </div>
          <div className="flex-1">
            <div className="font-semibold text-[15px]">Preferenze cookie</div>
            <div className="text-[13px] text-[#52525B] mt-0.5">
              {consent?.analytics
                ? "Hai acconsentito ai cookie di analisi (Google Analytics, PostHog). Non vengono comunque mai usati per registrare le sessioni qui nel gestionale."
                : "Al momento sono attivi solo i cookie tecnici necessari: hai rifiutato (o non ancora scelto) i cookie di analisi."}
            </div>
            <button
              onClick={openPreferences}
              className="mt-3 flex items-center gap-1.5 px-4 py-2 border border-[#E4E4E1] hover:bg-[#F9F9F8] rounded-md text-[13px] font-medium transition-colors"
            >
              <Cookie className="w-3.5 h-3.5" /> Cambia preferenze
            </button>
          </div>
        </div>
      </div>

      <div className="border border-[#DC2626]/30 bg-[#FEF2F2] rounded-lg p-5">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-md bg-white flex items-center justify-center shrink-0">
            <Trash2 className="w-5 h-5 text-[#DC2626]" />
          </div>
          <div className="flex-1">
            <div className="font-semibold text-[15px] text-[#DC2626]">Elimina definitivamente il tuo account</div>
            <div className="text-[13px] text-[#52525B] mt-0.5">
              Cancella in modo permanente e irreversibile il tuo account e tutti i dati collegati (clienti, offerte, documenti, provvigioni, conversazioni AI) — il tuo diritto all'oblio (art. 17 GDPR).
              Se hai un abbonamento attivo, verrà disdetto automaticamente. <strong>Questa azione non può essere annullata.</strong>
            </div>
            {!deleteOpen ? (
              <button
                onClick={() => setDeleteOpen(true)}
                className="mt-3 flex items-center gap-1.5 px-4 py-2 border-2 border-[#DC2626] text-[#DC2626] hover:bg-[#DC2626] hover:text-white rounded-md text-[13px] font-medium transition-colors"
              >
                <Trash2 className="w-3.5 h-3.5" /> Elimina il mio account
              </button>
            ) : (
              <div className="mt-4 bg-white border border-[#E4E4E1] rounded-md p-4 space-y-3">
                <div className="flex items-start gap-2 text-[12px] text-[#B45309]">
                  <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                  Per confermare, inserisci la tua password e scrivi <strong>ELIMINA</strong> nel campo qui sotto.
                </div>
                <div className="relative">
                  <input
                    type={deletePasswordVisible ? "text" : "password"}
                    value={deletePassword}
                    onChange={(e) => setDeletePassword(e.target.value)}
                    placeholder="La tua password attuale"
                    className="w-full border border-[#E4E4E1] rounded-md px-3 py-2 pr-9 text-[13px]"
                  />
                  <button
                    type="button"
                    onClick={() => setDeletePasswordVisible((v) => !v)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-[#6B6B72]"
                  >
                    {deletePasswordVisible ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                <input
                  value={deleteConfirmText}
                  onChange={(e) => setDeleteConfirmText(e.target.value)}
                  placeholder='Scrivi "ELIMINA" per confermare'
                  className="w-full border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]"
                />
                <div className="flex gap-2">
                  <button
                    onClick={deleteMyAccount}
                    disabled={deleting || deleteConfirmText !== "ELIMINA" || !deletePassword}
                    className="flex items-center gap-1.5 px-4 py-2 bg-[#DC2626] hover:bg-[#B91C1C] text-white rounded-md text-[13px] font-medium disabled:opacity-40 transition-colors"
                  >
                    {deleting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
                    {deleting ? "Eliminazione in corso…" : "Conferma eliminazione definitiva"}
                  </button>
                  <button
                    onClick={() => { setDeleteOpen(false); setDeletePassword(""); setDeleteConfirmText(""); }}
                    disabled={deleting}
                    className="px-4 py-2 border border-[#E4E4E1] rounded-md text-[13px] font-medium text-[#52525B]"
                  >
                    Annulla
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
