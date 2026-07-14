import { Link } from "react-router-dom";
import { Helmet } from "react-helmet-async";

export default function Privacy() {
  return (
    <div className="min-h-screen bg-[#F9F9F8] flex flex-col">
      <Helmet>
        <title>Informativa Privacy — SALESFLY</title>
        <meta name="robots" content="noindex" />
      </Helmet>

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
            Bozza — versione 1.0 del 14/07/2026. Documento da far verificare da un professionista
            legale/DPO prima della pubblicazione definitiva, in base ai trattamenti realmente
            effettuati e alla struttura societaria.
          </p>
        </div>

        <section>
          <h2 className="font-bold text-base mb-1">1. Titolare del trattamento</h2>
          <p>
            Il Titolare del trattamento dei dati raccolti tramite il presente sito e il form
            di richiesta demo è [Ragione sociale/Nome e Cognome del titolare], con sede in
            [indirizzo], contattabile all'indirizzo email [email di contatto].
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
        </section>

        <section>
          <h2 className="font-bold text-base mb-1">3. Finalità del trattamento</h2>
          <p>I dati raccolti sono trattati per le seguenti finalità:</p>
          <ul className="list-disc pl-5 mt-1 space-y-0.5">
            <li>
              <strong>Erogazione del servizio richiesto</strong> (invio via email del link di
              accesso alla versione demo del CRM SALESFLY) — base giuridica: esecuzione di
              misure precontrattuali richieste dall'interessato (art. 6.1.b GDPR);
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
            ricevere l'accesso alla demo; il mancato conferimento comporta l'impossibilità di
            evadere la richiesta. Il consenso alle comunicazioni commerciali è facoltativo.
          </p>
        </section>

        <section>
          <h2 className="font-bold text-base mb-1">5. Modalità e durata della conservazione</h2>
          <p>
            I dati sono trattati con strumenti informatici e conservati su infrastrutture
            cloud (database e servizio di invio email) con misure di sicurezza adeguate. I
            dati relativi alle richieste demo sono conservati per il tempo necessario a
            gestire la richiesta e, in assenza di ulteriori interazioni, per un massimo di
            [24 mesi], salvo consenso a finalità di marketing perdurante o obblighi di legge
            diversi.
          </p>
        </section>

        <section>
          <h2 className="font-bold text-base mb-1">6. Comunicazione e destinatari dei dati</h2>
          <p>
            I dati possono essere comunicati a soggetti terzi che agiscono in qualità di
            responsabili del trattamento per conto del Titolare, tra cui: il fornitore del
            servizio di invio email (Resend), il fornitore di hosting del database e
            dell'infrastruttura cloud (Railway/MongoDB), il fornitore di hosting del sito
            (Netlify). Tali soggetti trattano i dati esclusivamente per le finalità sopra
            indicate e nel rispetto della normativa applicabile.
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
            <li>accesso ai propri dati personali;</li>
            <li>rettifica o cancellazione degli stessi;</li>
            <li>limitazione del trattamento;</li>
            <li>opposizione al trattamento;</li>
            <li>portabilità dei dati;</li>
            <li>revoca del consenso in qualsiasi momento, senza pregiudicare la liceità del
              trattamento basata sul consenso prestato prima della revoca (in particolare, è
              possibile revocare in ogni momento il consenso alle comunicazioni commerciali);</li>
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
