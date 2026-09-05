# SALESFLY

CRM per agenti di commercio plurimandatari: clienti, agenda e giro visite, offerte, provvigioni (con calcolo fiscale automatico), pipeline lead, mappa clienti, documenti, un modulo Personale/Flotta opzionale per chi gestisce anche dipendenti e veicoli, e un assistente AI in grado di leggere e scrivere nel CRM.

Sito pubblico e app: [salesfly.it](https://salesfly.it) — backend su Railway, frontend su Netlify, database MongoDB Atlas.

Questo README copre il progetto nel suo complesso. Per dettagli specifici a una parte, vedi anche [backend/README.md](backend/README.md) (gestione dipendenze Python con `uv`) e [frontend/README.md](frontend/README.md).

## Architettura

```
frontend/   React + Vite, SPA con prerendering statico (SEO), Tailwind CSS
            → Netlify (build statica, nessun server Node in produzione)

backend/    FastAPI (Python), ~40 router / ~50 servizi, MongoDB via pymongo async
            → Railway (Railpack, root directory /backend)
```

Il frontend non parla mai direttamente con Railway: ogni chiamata `/api/*` fatta dal browser resta sulla stessa origin (`salesfly.it`) e viene inoltrata al backend da un redirect Netlify (`frontend/public/_redirects`). Stesso principio per gli header di sicurezza (`frontend/public/_headers`). La configurazione di build (base directory, comando, publish directory) è in `netlify.toml` alla radice del repo, non nelle impostazioni del sito su Netlify — versionata e rivedibile in una PR come il resto.

Servizi esterni usati dal backend: MongoDB Atlas (dati), S3/S3-compatibile (documenti), Stripe e PayPal (abbonamenti, sempre come redirect a checkout ospitato, mai SDK/iframe embeddato), Google Calendar (sync appuntamenti, OAuth), Anthropic Claude (assistente AI), Resend (email transazionali), OpenRouteService (percorso ottimizzato, opzionale), Sentry e OpenTelemetry (osservabilità, opzionali).

## Requisiti

- **Python 3.12** (pin in `backend/.python-version`) e [uv](https://docs.astral.sh/uv/) per le dipendenze backend
- **Node.js 24** e npm per il frontend
- Un'istanza **MongoDB** raggiungibile (locale, o un cluster Atlas anche gratuito)
- Facoltativo: **Docker**, se vuoi testare in locale l'upload documenti con MinIO invece di un bucket S3 reale (stesso setup usato in CI, vedi `.github/workflows/ci.yml`)

## Installazione backend

```bash
cd backend
uv sync
cp .env.example .env
```

Poi valorizza almeno le variabili obbligatorie in `.env` (vedi [Variabili ambiente](#variabili-ambiente) sotto) — l'elenco completo, con descrizioni, è comunque `backend/core/config.py`, con i default usati quando una variabile è assente.

## Installazione frontend

```bash
cd frontend
npm install
```

Crea `frontend/.env.development.local` con:

```
VITE_BACKEND_URL=http://localhost:8000
```

## Variabili ambiente

Tutte lette in `backend/core/config.py`. Quelle senza default hanno un fallback che disattiva silenziosamente la funzionalità collegata (commentato caso per caso nel file), tranne `JWT_SECRET`, `MONGO_URL` e `DB_NAME`: senza queste il backend non si avvia.

**Obbligatorie**
| Variabile | Uso |
|---|---|
| `JWT_SECRET` | firma dei token di accesso — il backend rifiuta di avviarsi senza |
| `MONGO_URL`, `DB_NAME` | connessione MongoDB |

**Storage documenti (S3 o compatibile)**
| Variabile | Uso |
|---|---|
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | credenziali |
| `AWS_S3_BUCKET` (o `S3_BUCKET`) | bucket |
| `AWS_REGION` (o `S3_REGION`) | regione, default `eu-west-1` |
| `S3_ENDPOINT` | solo per un provider S3-compatibile non-AWS (es. MinIO in locale/CI); vuoto = AWS S3 reale |

**Stripe**
| Variabile | Uso |
|---|---|
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` | API e verifica webhook |
| `STRIPE_PRICE_BASE`, `STRIPE_PRICE_PRO` | price id dei due piani |

**PayPal**
| Variabile | Uso |
|---|---|
| `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET` | API |
| `PAYPAL_MODE` | `sandbox` (default) o `live` |
| `PAYPAL_WEBHOOK_ID` | verifica webhook |
| `PAYPAL_PLAN_BASE`, `PAYPAL_PLAN_PRO` | plan id dei due piani |

**Google Calendar**
| Variabile | Uso |
|---|---|
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` | OAuth |
| `GOOGLE_REAUTH_NOTIFY_COOLDOWN_HOURS` | frequenza avviso se il token va riautorizzato, default 24h |

**AI**
| Variabile | Uso |
|---|---|
| `ANTHROPIC_API_KEY` | chiave Claude — senza, l'assistente AI risponde con errore |

**Altre (tutte opzionali, con default o funzionalità disattivata)**
| Variabile | Uso |
|---|---|
| `CORS_ORIGINS` | origin consentite, default già impostato per salesfly.it |
| `TRIAL_DAYS` | durata prova gratuita, default 14 |
| `ORS_API_KEY` | OpenRouteService per il percorso ottimizzato — vuoto: stima in linea d'aria (haversine) |
| `RESEND_API_KEY`, `APP_FROM_EMAIL` | invio email transazionali |
| `ADMIN_NOTIFY_EMAIL`, `CONTACT_NOTIFY_EMAIL` | destinatari notifiche interne / form contatti |
| `SENTRY_DSN` | error tracking — vuoto: disattivato |
| `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_SERVICE_NAME` | tracing OpenTelemetry — vuoto: disattivato |
| `AUTOMATION_ENGINE_INTERVAL_SECONDS`, `AUTOMATION_MAX_ATTEMPTS` | motore automazioni |
| `ADMIN_SECRET` | accesso agli endpoint di amministrazione |
| `FRONTEND_URL` | dove reindirizzare dopo il callback OAuth Google |
| `TRUSTED_PROXY_HOPS` | quanti hop di reverse proxy fidati davanti al backend (Railway = 1, il default) |

**Frontend** (`frontend/.env.development.local` in locale, variabile d'ambiente su Netlify in produzione)
| Variabile | Uso |
|---|---|
| `VITE_BACKEND_URL` | solo in sviluppo locale — in produzione il frontend chiama sempre `/api/*` sulla stessa origin, instradato da Netlify |

## Avvio locale

```bash
# backend — http://localhost:8000
cd backend
uv run python -m uvicorn server:app --reload

# frontend — http://localhost:3000
cd frontend
npm start
```

## Test

```bash
# backend — 114 file, pytest
cd backend
uv run pytest -q

# frontend — lint + build (nessuna suite di test automatizzata al momento)
cd frontend
npm run lint
npm run build
```

La pipeline CI (`.github/workflows/ci.yml`, su ogni PR verso `main`) esegue: lint + type check + pytest sul backend (con MongoDB e MinIO come container effimeri, non servizi remoti condivisi), lint + build sul frontend. Due test AI reali e due test PWA restano deselezionati in CI per motivi documentati direttamente nel workflow (richiedono rispettivamente una chiave Anthropic reale e il proxy Netlify davanti al backend, non riproducibile in un job che avvia solo il backend nudo).

C'è inoltre una pipeline separata di **smoke test** (`.github/workflows/smoke-test.yml`, cartella `smoke-tests/`) che verifica `https://salesfly.it` reale — non il codice, l'ambiente di produzione effettivo — a ogni push su `main` e ogni 30 minuti.

## Deployment

- **Backend → Railway**: root directory `/backend`, rilevamento automatico (Railpack) di `pyproject.toml` + `uv.lock` + `.python-version`, nessun build command custom.
- **Frontend → Netlify**: base directory, build command (che esegue anche il prerendering statico delle pagine pubbliche e rigenera `sitemap.xml`) e publish directory sono in `netlify.toml` alla radice del repo, non nella UI di Netlify. Redirect (`/api/*` verso Railway) e header di sicurezza restano invece file (`_redirects`, `_headers`) in `frontend/public/` — letti da Netlify dalla cartella pubblicata, non da `netlify.toml`.
- Entrambi si deployano automaticamente al merge su `main`, dopo che la CI è verde.

## Migrazioni

`backend/migrations/_NNN_descrizione.py` — file numerati in ordine (`_001_`, `_002_`, ...), eseguiti automaticamente all'avvio del backend (`migrations/runner.py`) e tracciati in `db.schema_migrations`: ogni migrazione gira una sola volta, mai due, anche con più repliche Railway avviate contemporaneamente sullo stesso deploy.

Per aggiungerne una: crea un nuovo file `_00N_descrizione.py` in `backend/migrations/` con una funzione `run()` (vedi i file esistenti come esempio) — non serve registrarlo altrove, `runner.py` lo scopre da solo.

## Backup

La protezione dei dati si affida in primo luogo ai backup nativi di **MongoDB Atlas** (Atlas → cluster → tab *Backup*), non a qualcosa che il codice di questo repo controlli o garantisca. Da verificare periodicamente direttamente lì, non assunto:

- Se i backup automatici sono attivi sul cluster in uso (dipende dal tier: **i cluster gratuiti M0 non li includono**, disponibili solo da M10 in su).
- La finestra di retention e se è disponibile il point-in-time recovery.
- Come si esegue un ripristino in pratica (Atlas → *Backup* → snapshot → *Restore*) — vale la pena provarlo almeno una volta su un cluster di test, non solo leggerlo, prima che serva davvero in produzione.

**Su un cluster M0** (nessun backup automatico di Atlas), `backend/scripts/backup_local.ps1` è un compromesso a costo zero: un dump manuale con `mongodump`, da lanciare ogni tanto, non un sostituto di un vero backup gestito.

```powershell
# Richiede MongoDB Database Tools (mongodump) nel PATH:
# https://www.mongodb.com/try/download/database-tools
cd backend
.\scripts\backup_local.ps1
```

Legge `MONGO_URL`/`DB_NAME` da `backend/.env` se non passati esplicitamente (`-Uri`/`-Database`), salva in `backups/<data>/` alla radice del repo (mai committata, esclusa in `.gitignore`), e cancella in automatico i backup più vecchi di 14 giorni (`-KeepDays 0` per disattivare la pulizia).
