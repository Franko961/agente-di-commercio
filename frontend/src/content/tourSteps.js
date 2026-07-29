// Contenuto condiviso tra il tour pubblico (/tour, pre-login) e la mini-guida
// mostrata dentro l'app al primo accesso (Layout.jsx) — stesso testo e
// stessi mockup, per non mantenere due copie della stessa cosa.
import {
  DashboardVisual, ClientiVisual, LeadVisual, AgendaVisual,
  AutomazioniVisual, AIVisual, GiroVisiteVisual,
} from "@/components/AppVisuals";

export const TOUR_STEPS = [
  {
    title: "Dashboard",
    sentence: "Un cruscotto che mostra subito cosa fare oggi: visite, offerte in scadenza e quanto manca al tuo obiettivo mensile.",
    Visual: DashboardVisual,
  },
  {
    title: "Clienti",
    sentence: "Tutti i tuoi clienti, contatti e storico visite in un unico posto, sempre a portata di mano.",
    Visual: ClientiVisual,
  },
  {
    title: "Lead",
    sentence: "Traccia ogni trattativa in una pipeline visuale, dalla prima chiamata alla firma.",
    Visual: LeadVisual,
  },
  {
    title: "Agenda",
    sentence: "Appuntamenti e promemoria organizzati automaticamente, senza dimenticare nessuna visita.",
    Visual: AgendaVisual,
  },
  {
    title: "Automazioni",
    sentence: "SalesFly può ricordarti automaticamente di contattare clienti, lead e offerte in scadenza.",
    Visual: AutomazioniVisual,
  },
  {
    title: "Assistente AI",
    sentence: "Parla o scrivi all'assistente: aggiunge clienti, appuntamenti e note al posto tuo.",
    Visual: AIVisual,
  },
  {
    title: "Giro visite",
    sentence: "Pianifica il giro visita ottimale e salvalo direttamente in agenda con un clic.",
    Visual: GiroVisiteVisual,
  },
];
