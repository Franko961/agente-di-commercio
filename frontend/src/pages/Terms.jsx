import { Link } from "react-router-dom";

export default function Terms() {
  return (
    <div className="min-h-screen bg-[#F9F9F8] flex flex-col">
      <title>Termini di Servizio — SALESFLY</title>
      <meta name="robots" content="noindex" />

      <header className="border-b border-[#E4E4E1] bg-white px-6 py-4 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2">
          <div className="w-9 h-9 flex items-center justify-center shrink-0">
            <img src="/logo-mark.png" alt="SALESFLY" className="w-full h-full object-contain" />
          </div>
          <span className="font-cabinet font-black text-lg">SALESFLY.</span>
        </Link>
        <Link to="/" className="text-[13px] text-[#52525B] hover:text-[#0A192F]">Torna al sito</Link>
      </header>

      <main className="flex-1 px-6 py-16 max-w-2xl mx-auto w-full text-sm text-[#333] leading-relaxed space-y-6">
        <div>
          <h1 className="font-cabinet font-black text-3xl mb-2">Termini di Servizio</h1>
          <p className="text-[#52525B] text-xs">
            Bozza — versione 1.0 del 26/07/2026. Documento da far verificare da un professionista
            legale prima della pubblicazione definitiva, in base alla struttura societaria e alle
            condizioni commerciali effettivamente offerte.
          </p>
        </div>

        <section>
          <h2 className="font-bold text-base mb-1">1. Chi siamo</h2>
          <p>
            SALESFLY è un servizio SaaS (Software as a Service) fornito da Franco Bruni, con sede
            in Via Cristoforo Colombo 179, 64014 Martinsicuro (TE), P.IVA 02121430678,
            contattabile all'indirizzo email franco.bruni.art@gmail.com ("il Fornitore").
            L'utilizzo del servizio SALESFLY, raggiungibile all'indirizzo salesfly.it
            ("il Servizio"), comporta l'accettazione integrale dei presenti Termini di Servizio.
          </p>
        </section>

        <section>
          <h2 className="font-bold text-base mb-1">2. Descrizione del servizio</h2>
          <p>
            SALESFLY è un gestionale (CRM) pensato per agenti di commercio plurimandatari, che
            consente tra l'altro di: gestire anagrafiche di clienti, lead e mandanti; pianificare
            appuntamenti e sincronizzarli facoltativamente con Google Calendar; creare offerte,
            ordini e monitorare provvigioni e spese; archiviare documenti; utilizzare un
            assistente basato su intelligenza artificiale per supportare l'attività commerciale;
            configurare automazioni personalizzate che eseguono azioni (promemoria, attività,
            email) al verificarsi di condizioni impostate dall'utente.
          </p>
        </section>

        <section>
          <h2 className="font-bold text-base mb-1">3. Account e registrazione</h2>
          <p>
            Per utilizzare il Servizio è necessario registrare un account fornendo dati veritieri
            e mantenerli aggiornati. L'utente è responsabile della riservatezza delle proprie
            credenziali di accesso e di ogni attività svolta tramite il proprio account. È vietato
            condividere le credenziali con terzi o consentire l'accesso a persone non autorizzate.
          </p>
        </section>

        <section>
          <h2 className="font-bold text-base mb-1">4. Piano di prova e abbonamenti</h2>
          <p>
            Il Servizio può essere provato gratuitamente per il periodo di prova indicato al
            momento della registrazione. Al termine del periodo di prova, o se non attivato un
            piano di prova, l'accesso continuativo al Servizio richiede la sottoscrizione di un
            abbonamento a pagamento tra quelli disponibili, con addebito ricorrente secondo la
            periodicità e le modalità di pagamento scelte (es. Stripe, PayPal). L'utente può
            disdire l'abbonamento in qualsiasi momento dalle proprie Impostazioni; salvo diversa
            indicazione, la disdetta ha effetto dalla fine del periodo di fatturazione in corso,
            senza rimborso pro-quota per il periodo già iniziato.
          </p>
        </section>

        <section>
          <h2 className="font-bold text-base mb-1">5. Dati inseriti dall'utente</h2>
          <p>
            L'utente resta l'unico responsabile dell'accuratezza, liceità e correttezza dei dati
            che inserisce nel Servizio, inclusi i dati personali di propri clienti, lead o
            contatti terzi. L'utente garantisce di avere una base giuridica adeguata (es.
            consenso, rapporto contrattuale o precontrattuale in corso) per trattare tali dati
            personali di terzi tramite SALESFLY, e di rispettare la normativa privacy applicabile
            (GDPR) nei confronti di tali terzi. Il Fornitore tratta questi dati in qualità di
            responsabile del trattamento per conto dell'utente, secondo quanto descritto
            nell'<Link to="/privacy" className="underline">Informativa Privacy</Link>.
          </p>
        </section>

        <section>
          <h2 className="font-bold text-base mb-1">6. Integrazioni con servizi terzi</h2>
          <p>
            Il Servizio consente di collegare facoltativamente integrazioni con servizi terzi
            (es. Google Calendar per la sincronizzazione degli appuntamenti, Resend per l'invio
            di email). L'attivazione di tali integrazioni è a discrezione dell'utente e comporta
            l'accettazione delle condizioni d'uso del rispettivo servizio terzo. Il Fornitore non
            è responsabile per interruzioni, modifiche o cessazioni del servizio da parte di tali
            terzi, né per la conseguente indisponibilità temporanea delle funzionalità di
            sincronizzazione.
          </p>
        </section>

        <section>
          <h2 className="font-bold text-base mb-1">7. Assistente basato su intelligenza artificiale</h2>
          <p>
            Il Servizio include funzionalità basate su modelli di intelligenza artificiale di
            terze parti, utilizzati per generare risposte, suggerimenti e, se autorizzato
            dall'utente, per proporre azioni sui dati del CRM (es. creazione di un'offerta),
            sempre soggette a conferma esplicita dell'utente prima dell'esecuzione definitiva.
            Le risposte generate dall'intelligenza artificiale possono contenere imprecisioni:
            l'utente è tenuto a verificarne la correttezza prima di farvi affidamento per
            decisioni commerciali o operative.
          </p>
        </section>

        <section>
          <h2 className="font-bold text-base mb-1">8. Automazioni personalizzate</h2>
          <p>
            L'utente può configurare regole di automazione che, al verificarsi delle condizioni
            impostate, eseguono in autonomia azioni quali l'invio di promemoria o email di
            follow-up a propri clienti o lead. L'utente è responsabile del contenuto e della
            liceità di tali comunicazioni automatiche, incluso il rispetto della normativa
            applicabile in materia di comunicazioni commerciali (es. consenso del destinatario,
            ove richiesto).
          </p>
        </section>

        <section>
          <h2 className="font-bold text-base mb-1">9. Utilizzi vietati</h2>
          <p>È vietato utilizzare il Servizio per:</p>
          <ul className="list-disc pl-5 mt-1 space-y-0.5">
            <li>finalità illecite o in violazione di normative applicabili;</li>
            <li>tentare di accedere senza autorizzazione a sistemi, dati o account di altri utenti;</li>
            <li>interferire con il normale funzionamento del Servizio o dell'infrastruttura che lo eroga;</li>
            <li>inviare comunicazioni non richieste (spam) tramite le funzionalità email/automazioni del Servizio.</li>
          </ul>
        </section>

        <section>
          <h2 className="font-bold text-base mb-1">10. Disponibilità e modifiche al servizio</h2>
          <p>
            Il Fornitore si impegna a mantenere il Servizio disponibile con la massima diligenza,
            ma non garantisce un funzionamento ininterrotto o privo di errori. Il Fornitore si
            riserva il diritto di modificare, sospendere o interrompere funzionalità del Servizio,
            dandone ove possibile ragionevole preavviso, in particolare per modifiche che
            riducano sostanzialmente le funzionalità di un piano a pagamento attivo.
          </p>
        </section>

        <section>
          <h2 className="font-bold text-base mb-1">11. Limitazione di responsabilità</h2>
          <p>
            Nei limiti massimi consentiti dalla legge applicabile, il Fornitore non è responsabile
            per danni indiretti, perdita di profitti, dati o opportunità commerciali derivanti
            dall'uso o dall'impossibilità di utilizzare il Servizio, salvo i casi di dolo o colpa
            grave. Nulla nei presenti Termini esclude o limita responsabilità che non possono
            essere escluse o limitate per legge.
          </p>
        </section>

        <section>
          <h2 className="font-bold text-base mb-1">12. Cancellazione dell'account</h2>
          <p>
            L'utente può richiedere la cancellazione del proprio account in qualsiasi momento
            dalle Impostazioni del profilo. La cancellazione comporta l'eliminazione definitiva
            e irreversibile di tutti i dati associati all'account, come descritto
            nell'<Link to="/privacy" className="underline">Informativa Privacy</Link>.
          </p>
        </section>

        <section>
          <h2 className="font-bold text-base mb-1">13. Legge applicabile e foro competente</h2>
          <p>
            I presenti Termini sono regolati dalla legge italiana. Per qualsiasi controversia
            relativa alla loro interpretazione o esecuzione sarà competente il foro del luogo di
            residenza o domicilio del consumatore, ove applicabile; negli altri casi, il foro
            competente sarà quello di residenza del Fornitore.
          </p>
        </section>

        <section>
          <h2 className="font-bold text-base mb-1">14. Modifiche ai presenti Termini</h2>
          <p>
            Il Fornitore si riserva il diritto di modificare i presenti Termini di Servizio.
            Eventuali modifiche sostanziali saranno comunicate agli utenti con adeguato preavviso;
            la prosecuzione nell'uso del Servizio dopo l'entrata in vigore delle modifiche
            costituisce accettazione delle stesse.
          </p>
        </section>
      </main>
    </div>
  );
}
