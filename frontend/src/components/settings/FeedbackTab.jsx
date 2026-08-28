import { useState } from "react";
import { CheckCircle2, Star, Save } from "lucide-react";
import { toast } from "sonner";
import { submitFeedback } from "../../api/feedback";

export default function FeedbackTab() {
  const [fbRating, setFbRating] = useState(0);
  const [fbText, setFbText] = useState("");
  const [fbConsent, setFbConsent] = useState(false);
  const [fbBusy, setFbBusy] = useState(false);
  const [fbSent, setFbSent] = useState(false);

  // Rinominato rispetto all'originale (era anch'esso "submitFeedback"):
  // quel nome oscurava l'import di api/feedback.js per tutto lo scope del
  // componente, quindi la chiamata "await submitFeedback(...)" richiamava
  // se stessa invece della funzione API — il form non ha mai davvero
  // inviato nulla al backend (bug introdotto durante la migrazione
  // all'astrazione API, corretto qui).
  const handleFeedbackSubmit = async (e) => {
    e.preventDefault();
    if (!fbRating) { toast.error("Seleziona un voto da 1 a 5 stelle"); return; }
    setFbBusy(true);
    try {
      await submitFeedback({ rating: fbRating, text: fbText.trim(), publish_consent: fbConsent });
      setFbSent(true);
      setFbRating(0);
      setFbText("");
      setFbConsent(false);
      toast.success("Grazie per il tuo feedback!");
    } catch {
      toast.error("Invio non riuscito, riprova tra poco");
    } finally {
      setFbBusy(false);
    }
  };

  return (
    <>
      <div className="mb-8">
        <div className="font-mono text-[11px] uppercase tracking-widest text-[#B23E00] mb-1">Impostazioni</div>
        <h1 className="font-cabinet text-3xl font-black">Feedback</h1>
        <p className="text-[#52525B] mt-1">
          Raccontaci come va con SALESFLY — ci aiuta a migliorare, e con il tuo consenso può comparire come recensione sul sito.
        </p>
      </div>

      {fbSent ? (
        <div className="border border-[#E4E4E1] rounded-lg p-6 text-center">
          <CheckCircle2 className="w-8 h-8 text-[#16A34A] mx-auto mb-3" />
          <div className="font-cabinet font-bold text-[16px] mb-1">Grazie per il tuo feedback!</div>
          <p className="text-[13px] text-[#52525B]">L'abbiamo ricevuto. Puoi inviarne un altro quando vuoi.</p>
          <button
            onClick={() => setFbSent(false)}
            className="mt-4 text-[13px] font-medium text-[#0A192F] underline underline-offset-4"
          >
            Invia un altro feedback
          </button>
        </div>
      ) : (
        <form onSubmit={handleFeedbackSubmit} className="border border-[#E4E4E1] rounded-lg p-5 space-y-5">
          <div>
            <label className="block text-[12px] font-semibold text-[#52525B] mb-2">Voto</label>
            <div className="flex items-center gap-1">
              {[1, 2, 3, 4, 5].map((n) => (
                <button
                  key={n}
                  type="button"
                  data-testid={`feedback-star-${n}`}
                  onClick={() => setFbRating(n)}
                  className="p-0.5"
                  aria-label={`${n} stelle`}
                >
                  <Star
                    className={`w-7 h-7 transition-colors ${n <= fbRating ? "fill-[#B23E00] text-[#B23E00]" : "text-[#E4E4E1]"}`}
                  />
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-[12px] font-semibold text-[#52525B] mb-1.5">Il tuo commento (opzionale)</label>
            <textarea
              data-testid="feedback-text-input"
              value={fbText}
              onChange={(e) => setFbText(e.target.value)}
              rows={4}
              placeholder="Cosa ti piace? Cosa cambieresti?"
              className="w-full px-3 py-2 border border-[#E4E4E1] rounded-md text-[14px] focus:outline-none focus:border-[#B23E00]"
            />
          </div>
          <label className="flex items-start gap-2 text-[13px] text-[#52525B]">
            <input
              type="checkbox"
              data-testid="feedback-publish-consent"
              checked={fbConsent}
              onChange={(e) => setFbConsent(e.target.checked)}
              className="mt-0.5"
            />
            <span>Autorizzo la pubblicazione di questa recensione sul sito, anche con il mio nome. Verrà comunque controllata prima di essere pubblicata.</span>
          </label>
          <button
            type="submit"
            disabled={fbBusy}
            data-testid="feedback-submit-button"
            className="flex items-center gap-1.5 px-4 py-2 bg-[#B23E00] hover:bg-[#E04F00] text-white rounded-md text-[13px] font-medium transition-colors disabled:opacity-50"
          >
            <Save className="w-3.5 h-3.5" /> {fbBusy ? "Invio…" : "Invia feedback"}
          </button>
        </form>
      )}
    </>
  );
}
