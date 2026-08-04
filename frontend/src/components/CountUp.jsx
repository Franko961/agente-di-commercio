import { useEffect, useRef, useState } from "react";
import useInView from "@/hooks/useInView";

const defaultFormatter = (n) => Math.round(n).toLocaleString("it-IT");

// Conta da 0 al valore finale quando il numero entra nello scroll (dati
// puramente decorativi in queste pagine pubbliche — vedi PhoneMockupScreen
// in Landing.jsx — non provengono mai da una vera sessione utente, quindi
// animarli non rischia di mostrare un dato reale "sbagliato" a metà conteggio).
export default function CountUp({ end, duration = 1200, prefix = "", suffix = "", formatter = defaultFormatter, className }) {
  const [ref, inView] = useInView();
  const [value, setValue] = useState(0);
  const started = useRef(false);

  useEffect(() => {
    if (!inView || started.current) return;
    started.current = true;
    const start = performance.now();
    let frame;
    const tick = (now) => {
      const progress = Math.min((now - start) / duration, 1);
      // ease-out cubic: parte veloce e rallenta in chiusura, più naturale
      // di un conteggio lineare.
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(end * eased);
      if (progress < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [inView, end, duration]);

  return (
    <span ref={ref} className={className}>
      {prefix}{formatter(value)}{suffix}
    </span>
  );
}
