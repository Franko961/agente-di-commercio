import React from "react";
import ReactDOM from "react-dom/client";
import "@/index.css";
import App from "@/App";

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

// Register Service Worker for PWA offline mode + auto-update
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    // Un controller già presente PRIMA della registrazione significa che
    // questa pagina era già sotto controllo di una versione precedente del
    // service worker (visita di ritorno): solo in quel caso un nuovo
    // controller che prende il posto del vecchio deve ricaricare la pagina
    // per servire il bundle aggiornato. Alla primissima visita in assoluto
    // non c'è nessun controller precedente da sostituire — ricaricare
    // comunque raddoppiava il tempo di caricamento di OGNI nuovo
    // visitatore (e di ogni scansione di Googlebot, che non ha mai un
    // service worker preesistente) senza alcun beneficio: verificato con
    // Lighthouse, ~3,7s persi per un secondo caricamento completo della
    // homepage che non serviva a nulla.
    const hadControllerBeforeRegister = !!navigator.serviceWorker.controller;
    navigator.serviceWorker.register("/sw.js").then((reg) => {
      // When a new SW takes control, reload once so the user gets the fresh JS bundle
      if (hadControllerBeforeRegister) {
        let refreshing = false;
        navigator.serviceWorker.addEventListener("controllerchange", () => {
          if (refreshing) return;
          refreshing = true;
          window.location.reload();
        });
      }
      // Force SW update check on every load
      reg.update?.().catch(() => {});

      // Un agente che tiene l'app aperta in background per ore (tra una
      // telefonata e l'altra, passando ad altre app) senza mai chiuderla del
      // tutto non farebbe mai ripassare da qui: il solo controllo al "load"
      // sopra basta per chi riapre l'app da zero, non per chi ci resta
      // dentro a lungo. Due controlli in più coprono quel caso: quando la
      // scheda torna in primo piano, e comunque ogni 30 minuti mentre resta
      // aperta — così anche senza mai chiuderla, l'aggiornamento arriva
      // entro poco tempo invece di restare bloccati a tempo indefinito su
      // una versione vecchia (vedi il caso reale che ha motivato l'aggiunta).
      document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "visible") reg.update?.().catch(() => {});
      });
      setInterval(() => reg.update?.().catch(() => {}), 30 * 60 * 1000);
    }).catch((err) => {
      console.warn("SW registration failed:", err);
    });
  });
}
