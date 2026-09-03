# Frontend — SALESFLY

React + [Vite](https://vitejs.dev/), Tailwind CSS. Deploy su Netlify (build statica, publish directory `build`).

## Script disponibili

```bash
npm start        # dev server, http://localhost:3000 (porta scelta per continuità con il precedente setup CRA)
npm run build     # vite build + prerendering statico delle pagine pubbliche (scripts/prerender.js) + sitemap.xml/llms.txt
npm run lint      # eslint
```

Non c'è una suite di test automatizzata per il frontend al momento — solo lint e build, entrambi gate in CI (`.github/workflows/ci.yml`).

## Variabili ambiente

`VITE_BACKEND_URL` (solo sviluppo locale, in `.env.development.local`) — in produzione il frontend chiama sempre `/api/*` sulla stessa origin, instradato verso il backend Railway da `public/_redirects`.

## Note

- Migrato da Create React App a Vite il 2026-08-23 — se trovi riferimenti residui a CRA altrove, sono da correggere.
- `public/_redirects` e `public/_headers` sono la configurazione Netlify (redirect API, header di sicurezza) — non esiste un `netlify.toml`.

Per il quadro generale del progetto (backend, variabili ambiente, deployment, migrazioni), vedi il [README alla radice del repo](../README.md).
