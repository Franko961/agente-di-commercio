import { Link } from "react-router-dom";

export default function Privacy() {
  return (
    <div className="min-h-screen bg-[#F9F9F8] flex flex-col">
      <title>Informativa Privacy — SALESFLY</title>
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
          <h1 className="font-cabinet font-black text-3xl mb-2">Informativa sulla Privacy</h1>
          <p className="text-[#52525B] text-xs">
            Bozza — versione 1.4 del 02/08/2026. Documento da far verificare da un professionista
            legale/DPO prima della pubblicazione definitiva, in base ai trattamenti realmente
            effettuati e alla struttura societaria.
          </p>
        </div>

        <section>
          <h2 className="font-bold text-base mb-1">1. Titolare del trattamento</h2>
          <p>
            Il Titolare del trattamento dei dati raccolti tramite il presente sito, il form di
            richiesta demo e l'applicazione SALESFLY è Franco Bruni, con sede in Via Cristoforo
            Colombo 179, 64014 Martinsicuro (TE), P.IVA 02121430678, contattabile all'indirizzo
            email franco.bruni.art@gmail.com.
          </p>
        </section>

        <section>
          <h2 className="font-bold text-base mb-1">2. Dati raccolti</h2>
          <p>Attraverso il form "Richiedi la Demo" raccogliamo i seguenti dati personali:</p>
          <ul className="list-disc pl-5 mt-1 space-y-0.5">
            <li>Nome e cognome</li>
            <li>Indirizzo email</li>
            <li>Azienda (facoltativo)</li>
            <li>Numero di telefono (facoltativo)</li>
            <li>Indirizzo IP e user agent del browser, registrati automaticamente come prova
              tecnica del consenso prestato</li>
            <li>Data e ora della richiesta</li>
          </ul>
          <p className="mt-2">
            Una volta attivato un account, l'applicazione tratta inoltre i dati che l'utente
            stesso inserisce per gestire la propria attività di agente di commercio: anagrafiche
            di clienti, lead e mandanti, appuntamenti, offerte, ordini, provvigioni e spese,
            documenti caricati. Questi dati sono di titolarità dell'utente stesso, che ne è
            autonomo titolare per i clienti/lead che gestisce; SALESFLY li tratta in qualità di
            responsabile del trattamento, secondo le istruzioni impartite dall'utente tramite
            l'uso dell'applicazione.
          </p>
        </section>

        <section>
          <h2 className="font-bold text-base mb-1">3. Finalità del trattamento</h2>
          <p>I dati raccolti sono trattati per le seguenti finalità:</p>
          <ul className="list-disc pl-5 mt-1 space-y-0.5">
            <li>
              <strong>Erogazione del servizio richiesto</strong> (invio via email del link di
              accesso alla versione demo del CRM SALESFLY, oppure erogazione del servizio in
              abbonamento all'utente registrato) — base giuridica: esecuzione di misure
              precontrattuali richieste dall'interessato o esecuzione del contratto di
              abbonamento (art. 6.1.b GDPR);
            </li>
            <li>
              <strong>Comunicazioni commerciali/marketing</strong> relative a SALESFLY (es.
              contatto commerciale, aggiornamenti sul prodotto) — solo se è stato espresso
              l'apposito consenso facoltativo — base giuridica: consenso dell'interessato
              (art. 6.1.a GDPR). Il mancato consenso a questa finalità non pregiudica in alcun
              modo l'accesso alla demo.
            </li>
          </ul>
        </section>

        <section>
          <h2 className="font-bold text-base mb-1">4. Natura del conferimento</h2>
          <p>
            Il conferimento dei dati contrassegnati come obbligatori è necessario per poter
            ricevere l'accesso alla demo o utilizzare il servizio in abbonamento; il mancato
            conferimento comporta l'impossibilità di evadere la richiesta o erogare il servizio.
            Il consenso alle comunicazioni commerciali è facoltativo.
          </p>
        </section>

        <section>
          <h2 className="font-bold text-base mb-1">5. Modalità e durata della conservazione</h2>
          <p>
            I dati sono trattati con strumenti informatici e conservati su infrastrutture cloud
            (database e servizio di invio email) con misure di sicurezza adeguate.
          </p>
          <ul className="list-disc pl-5 mt-1 space-y-0.5">
            <li>
              I dati relativi alle richieste demo sono conservati per il tempo necessario a
              gestire la richiesta e, in assenza di ulteriori interazioni, per un massimo di
              24 mesi, salvo consenso a finalità di marketing perdurante o obblighi di legge
              diversi.
            </li>
            <li>
              I dati inseriti nell'applicazione da un utente registrato (clienti, offerte,
              appuntamenti, ecc.) sono conservati per tutta la durata dell'account attivo. Alla
              cancellazione dell'account, richiedibile in qualsiasi momento dalle Impostazioni
              del profilo, tutti i dati vengono cancellati in modo definitivo e immediato
              (nessun periodo di conservazione residuo), inclusi i documenti caricati.
            </li>
            <li>
              I log tecnici di sicurezza e monitoraggio dell'infrastruttura sono conservati per
              un massimo di 30 giorni. I log di audit amministrativo relativi ad azioni compiute
              da personale con privilegi amministrativi su un account di un utente sono conservati
              senza scadenza predefinita, per finalità di responsabilità e sicurezza verso terzi;
              la sola voce registrata quando un utente cancella autonomamente il proprio account
              (a conferma che la richiesta fosse autenticata) è invece conservata per un massimo
              di 12 mesi e riporta l'indirizzo email solo in forma di hash, non in chiaro.
            </li>
          </ul>
        </section>

        <section>
          <h2 className="font-bold text-base mb-1">6. Comunicazione e destinatari dei dati</h2>
          <p>
            I dati possono essere comunicati a soggetti terzi che agiscono in qualità di
            responsabili del trattamento per conto del Titolare, tra cui: il fornitore del
            servizio di invio email (Resend), il fornitore di hosting del database e
            dell'infrastruttura cloud (Railway/MongoDB), il fornitore di hosting del sito
            (Netlify), il fornitore di archiviazione documenti (storage compatibile S3), e —
            solo per gli utenti che attivano volontariamente l'integrazione — Google LLC, per la
            sincronizzazione con Google Calendar (vedi punto 6-bis). Solo se viene prestato
            l'apposito consenso (vedi punto 6-ter), anche Google Ireland Limited (Google
            Analytics) e PostHog Inc. (PostHog). Tali soggetti trattano i dati esclusivamente per
            le finalità sopra indicate e nel rispetto della normativa applicabile.
          </p>
        </section>

        <section>
          <h2 className="font-bold text-base mb-1">6-bis. Integrazione con Google Calendar</h2>
          <p>
            L'applicazione offre, su base opzionale e attivabile dall'utente dalle Impostazioni,
            un'integrazione con Google Calendar per sincronizzare gli appuntamenti gestiti in
            SALESFLY con il calendario Google dell'utente, nelle due direzioni. Attivando
            l'integrazione, l'utente autorizza SALESFLY ad accedere — tramite il protocollo
            OAuth 2.0 di Google, con lo scope <code>calendar.events</code> — alla creazione,
            lettura, modifica e cancellazione di eventi sul proprio Google Calendar. SALESFLY
            non accede ad altri dati dell'account Google dell'utente. L'utente può revocare
            l'autorizzazione in qualsiasi momento dalle Impostazioni di SALESFLY o direttamente
            dalla pagina{" "}
            <a
              href="https://myaccount.google.com/permissions"
              target="_blank" rel="noreferrer"
              className="underline"
            >
              myaccount.google.com/permissions
            </a>
            . L'uso da parte di SALESFLY delle informazioni ricevute dalle API di Google rispetta
            la Google API Services User Data Policy, inclusi i requisiti di Limited Use.
          </p>
        </section>

        <section>
          <h2 className="font-bold text-base mb-1">6-ter. Cookie e strumenti di analisi</h2>
          <p>
            Il sito utilizza esclusivamente cookie tecnici strettamente necessari al
            funzionamento (es. il cookie di sessione che mantiene l'accesso effettuato), per i
            quali non è richiesto consenso (art. 122 Codice Privacy). Nessun cookie di analisi
            viene installato finché l'utente non esprime un consenso esplicito tramite il banner
            mostrato alla prima visita, revocabile in qualsiasi momento dal link "Preferenze
            cookie" nel piè di pagina del sito pubblico, o dalla sezione "Privacy e dati" delle
            Impostazioni per gli utenti registrati.
          </p>
          <p className="mt-2">
            Se il consenso viene prestato, vengono attivati:
          </p>
          <ul className="list-disc pl-5 mt-1 space-y-0.5">
            <li>
              <strong>Google Analytics</strong> (Google Ireland Limited) — statistiche aggregate
              di traffico e utilizzo del sito;
            </li>
            <li>
              <strong>PostHog</strong> (PostHog Inc., Stati Uniti) — statistiche di prodotto e,
              solo sulle pagine pubbliche del sito (landing, prezzi, blog, form contatti e
              richiesta demo), registrazione anonimizzata delle sessioni di navigazione, con i
              campi dei moduli sempre mascherati. La registrazione delle sessioni è
              tecnicamente disattivata nell'area riservata dell'applicazione (le pagine sotto
              "/app"), dove sono presenti anagrafiche clienti, importi, documenti e conversazioni
              con l'assistente AI, indipendentemente dal consenso prestato.
            </li>
          </ul>
          <p className="mt-2">
            Base giuridica: consenso dell'interessato (art. 6.1.a GDPR), revocabile in ogni
            momento senza pregiudicare la liceità del trattamento svolto prima della revoca. La
            conservazione dei dati raccolti da Google Analytics e PostHog è determinata dalle
            impostazioni di conservazione configurate direttamente in tali strumenti dal
            Titolare, periodicamente verificate per restare al minimo necessario alle finalità
            statistiche sopra indicate.
          </p>
        </section>

        <section>
          <h2 className="font-bold text-base mb-1">6-quater. Accesso al gestionale per finalità di assistenza</h2>
          <p>
            Il personale amministrativo del Titolare può, solo su richiesta esplicita
            dell'utente (ad esempio nell'ambito di una richiesta di assistenza telefonica o via
            email su una modifica specifica), accedere temporaneamente al gestionale dell'utente.
            Per impostazione predefinita l'accesso è in sola lettura: non consente alcuna
            modifica ai dati dell'utente. Solo quando la richiesta di assistenza lo richiede
            (ad esempio per correggere direttamente un dato su indicazione dell'utente), il
            personale amministrativo può accedere con permessi di scrittura, indicando
            preventivamente il motivo dell'intervento; quel motivo resta anch'esso nel registro
            interno di cui sotto. L'accesso avviene esclusivamente per fornire l'assistenza
            richiesta, mai per finalità di controllo, marketing o analisi. Ogni accesso di questo
            tipo è tracciato in un registro interno (chi lo ha effettuato, su quale account,
            quando, con quali permessi) conservato dal Titolare a fini di responsabilità (art.
            5.2 GDPR), e la sessione così ottenuta scade automaticamente entro un'ora. L'utente
            può richiedere informazioni sugli accessi effettuati sul proprio account esercitando
            i diritti di cui al punto 8.
          </p>
        </section>

        <section>
          <h2 className="font-bold text-base mb-1">7. Trasferimento dati extra-UE</h2>
          <p>
            Alcuni fornitori sopra indicati potrebbero trattare i dati su server situati al
            di fuori dello Spazio Economico Europeo. In tal caso, il trasferimento avviene
            sulla base di garanzie adeguate previste dal GDPR (es. Clausole Contrattuali
            Standard della Commissione Europea).
          </p>
        </section>

        <section>
          <h2 className="font-bold text-base mb-1">8. Diritti dell'interessato</h2>
          <p>In qualsiasi momento è possibile esercitare, contattando il Titolare ai recapiti sopra indicati, i diritti previsti dagli artt. 15-22 del GDPR, tra cui:</p>
          <ul className="list-disc pl-5 mt-1 space-y-0.5">
            <li>accesso ai propri dati personali (nell'applicazione, disponibile in autonomia
              dalle Impostazioni tramite l'esportazione dati);</li>
            <li>rettifica o cancellazione degli stessi (la cancellazione dell'account, sempre
              disponibile dalle Impostazioni, elimina definitivamente tutti i dati);</li>
            <li>limitazione del trattamento;</li>
            <li>opposizione al trattamento;</li>
            <li>portabilità dei dati;</li>
            <li>revoca del consenso in qualsiasi momento, senza pregiudicare la liceità del
              trattamento basata sul consenso prestato prima della revoca (in particolare, è
              possibile revocare in ogni momento il consenso alle comunicazioni commerciali e
              l'autorizzazione a Google Calendar);</li>
            <li>proporre reclamo al Garante per la Protezione dei Dati Personali (www.garanteprivacy.it).</li>
          </ul>
        </section>

        <section>
          <h2 className="font-bold text-base mb-1">9. Modifiche alla presente informativa</h2>
          <p>
            Il Titolare si riserva il diritto di modificare la presente informativa. Eventuali
            modifiche sostanziali saranno comunicate agli interessati con adeguato preavviso,
            ove richiesto dalla normativa applicabile.
          </p>
        </section>
      </main>
    </div>
  );
}
