import { useState } from "react";
import { ArrowRight } from "lucide-react";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { TOUR_STEPS } from "@/content/tourSteps";
import { useAuth } from "@/contexts/AuthContext";

// Mini-guida mostrata una sola volta al primo accesso in app (vedi
// Layout.jsx): stesso contenuto del tour pubblico /tour, ma dentro l'app
// vera invece che come pagina di marketing pre-login — pensata per chi si
// è appena registrato, non per chi sta ancora valutando se iscriversi
// (quel percorso resta il tour pubblico, invariato).
export default function OnboardingTour() {
  const { markOnboardingSeen } = useAuth();
  const [step, setStep] = useState(0);
  const isLast = step === TOUR_STEPS.length - 1;
  const current = TOUR_STEPS[step];
  const Visual = current.Visual;

  return (
    <Dialog open onOpenChange={(v) => !v && markOnboardingSeen()}>
      <DialogContent className="max-w-3xl">
        <div className="flex items-center justify-center gap-2 mb-6">
          {TOUR_STEPS.map((_, i) => (
            <div key={i} className={`h-1.5 rounded-full transition-all ${i === step ? "w-8 bg-[#B23E00]" : "w-1.5 bg-[#E4E4E1]"}`} />
          ))}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
          <div className="order-2 md:order-1">
            <Visual />
          </div>
          <div className="order-1 md:order-2 text-center md:text-left">
            <div className="font-mono text-[11px] uppercase tracking-widest text-[#B23E00] mb-2">
              {step + 1} di {TOUR_STEPS.length}
            </div>
            <h2 className="font-cabinet font-black text-2xl md:text-3xl tracking-tight mb-3">{current.title}</h2>
            <p className="text-[14px] text-[#52525B] mb-6">{current.sentence}</p>
            <div className="flex items-center gap-3 justify-center md:justify-start">
              {step > 0 && (
                <button
                  onClick={() => setStep((s) => s - 1)}
                  className="px-4 py-2 border-2 border-[#0A192F] text-[#0A192F] rounded-lg text-[13px] font-bold hover:bg-[#0A192F] hover:text-white transition-colors"
                >
                  Indietro
                </button>
              )}
              <button
                onClick={() => (isLast ? markOnboardingSeen() : setStep((s) => s + 1))}
                className="px-4 py-2 bg-[#B23E00] text-white rounded-lg text-[13px] font-bold hover:bg-[#e04e00] transition-colors flex items-center gap-2"
              >
                {isLast ? "Inizia" : "Avanti"} <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
            {!isLast && (
              <button onClick={markOnboardingSeen} className="mt-3 text-[12px] text-[#6B6B72] hover:text-[#52525B] underline">
                Salta
              </button>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
