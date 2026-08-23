import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import PublicHeader from "@/components/PublicHeader";
import PublicFooter from "@/components/PublicFooter";
import { TOUR_STEPS as STEPS } from "@/content/tourSteps";
import PageMeta from "@/components/PageMeta";

function WelcomeScreen({ onStart }) {
  return (
    <div className="text-center max-w-lg mx-auto">
      <div className="w-16 h-16 mx-auto mb-6">
        <img src="/logo-mark.png" alt="SALESFLY" className="w-full h-full object-contain" />
      </div>
      <h1 className="font-cabinet font-black text-4xl md:text-5xl tracking-tight mb-4">Benvenuto in SalesFly.</h1>
      <p className="text-[16px] md:text-[18px] text-[#52525B] mb-8">
        Ti bastano 3 minuti per imparare le funzioni principali.
      </p>
      <button
        onClick={onStart}
        data-testid="tour-start-button"
        className="px-7 py-3.5 bg-[#B23E00] text-white rounded-lg text-[15px] font-bold hover:bg-[#e04e00] transition-colors inline-flex items-center gap-2"
      >
        Inizia <ArrowRight className="w-4 h-4" />
      </button>
    </div>
  );
}

function TourStep({ step, index, total, onNext, onPrev, onSkip, isLast }) {
  const Visual = step.Visual;
  return (
    <div className="w-full max-w-4xl mx-auto">
      <div className="flex items-center justify-center gap-2 mb-10">
        {STEPS.map((_, i) => (
          <div key={i} className={`h-1.5 rounded-full transition-all ${i === index ? "w-8 bg-[#B23E00]" : "w-1.5 bg-[#E4E4E1]"}`} />
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-10 items-center">
        <div className="order-2 md:order-1">
          <Visual />
        </div>
        <div className="order-1 md:order-2 text-center md:text-left">
          <div className="font-mono text-[11px] uppercase tracking-widest text-[#B23E00] mb-2">
            {index + 1} di {total}
          </div>
          <h2 className="font-cabinet font-black text-3xl md:text-4xl tracking-tight mb-4">{step.title}</h2>
          <p className="text-[16px] text-[#52525B] mb-8">{step.sentence}</p>
          <div className="flex items-center gap-3 justify-center md:justify-start">
            {index > 0 && (
              <button
                onClick={onPrev}
                data-testid="tour-prev-button"
                className="px-5 py-2.5 border-2 border-[#0A192F] text-[#0A192F] rounded-lg text-[14px] font-bold hover:bg-[#0A192F] hover:text-white transition-colors"
              >
                Indietro
              </button>
            )}
            <button
              onClick={onNext}
              data-testid="tour-next-button"
              className="px-5 py-2.5 bg-[#B23E00] text-white rounded-lg text-[14px] font-bold hover:bg-[#e04e00] transition-colors flex items-center gap-2"
            >
              {isLast ? "Inizia gratis" : "Avanti"} <ArrowRight className="w-4 h-4" />
            </button>
          </div>
          {!isLast && (
            <button onClick={onSkip} className="mt-4 text-[13px] text-[#6B6B72] hover:text-[#52525B] underline">
              Salta il tour
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default function GuidedTour() {
  const [started, setStarted] = useState(false);
  const [step, setStep] = useState(0);
  const navigate = useNavigate();
  const isLast = step === STEPS.length - 1;

  return (
    <div className="min-h-screen bg-[#F9F9F8] flex flex-col">
      <PageMeta path="/tour" />

      <PublicHeader />

      <main className="flex-1 flex items-center justify-center px-6 py-16">
        {!started ? (
          <WelcomeScreen onStart={() => setStarted(true)} />
        ) : (
          <TourStep
            step={STEPS[step]}
            index={step}
            total={STEPS.length}
            isLast={isLast}
            onPrev={() => setStep((s) => Math.max(0, s - 1))}
            onNext={() => (isLast ? navigate("/richiedi-demo") : setStep((s) => s + 1))}
            onSkip={() => navigate("/")}
          />
        )}
      </main>

      <PublicFooter />
    </div>
  );
}
