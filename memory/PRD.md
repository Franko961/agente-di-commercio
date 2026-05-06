# PRD — Gestionale Agenti di Commercio

## Original Problem Statement
Build a complete sales agent management system (Italian "gestionale per agenti di commercio") covering: customer database, order/revenue history, segmentation, leads/prospects, automatic commissions (multi-mandate, accrued vs collected), agenda with visit routes & geolocation, quotes/offers with deadlines & follow-ups, reports & KPIs, multi-mandate (separate brands, price lists, commissions), document archive, automation pipeline, mobile-first + offline, AI suggestions, predictive sales analysis, WhatsApp/email integration, digital signature, ERP integration.

## Architecture
- **Backend**: FastAPI + Motor (MongoDB) + JWT (Bearer/cookie) + bcrypt
- **Frontend**: React 19 + Tailwind + Shadcn UI + Recharts + Leaflet + lucide-react
- **AI**: Gemini 3 Flash via emergentintegrations + EMERGENT_LLM_KEY
- **Design**: Swiss high-contrast + Sartorial Italian (Cabinet Grotesk + Manrope, Navy #0A192F + Warning Orange #FF5A00)

## Implemented (2026-02-06)
- Auth: JWT login/register/me/logout + admin seed
- 12 modules CRUD: Mandanti, Products & Listini, Clients (segmentation+geolocation), Leads (Kanban), Appointments (week view), Offers (line items+commission auto-creation), Commissions (maturato/incassato), Documents, Automations
- Dashboard with KPIs, monthly revenue chart, pipeline donut, by-zone bar chart, upcoming visits, monthly goal
- Leaflet map with custom orange pins for all geolocated clients
- AI Assistant chat (Gemini 3 Flash) + Suggestions panel
- Auto-seeded demo data (3 mandanti, 5 products, 8 clients across Italy, 5 leads, 7 appointments, 5 offers, 3 commissions, 3 documents, 3 automations)
- Mobile-first: bottom tab nav + drawer menu, card layouts vs tables
- Mandante context switcher (top header + sidebar)
- 100% backend tests pass (28/28), 100% frontend routes work

## Implemented P1 (2026-02-06 — second session)
- **PWA read-only offline**: manifest.json + service worker (`/sw.js`) caching all GET API responses (clienti, agenda, offerte, provvigioni, mandanti, products, leads, documents, automations, dashboard, auth/me); install banner + theme color #0A192F; OfflineBanner global indicator that defaults visible when navigator.onLine===false at mount
- **CSV exports** (UTF-8 BOM + semicolon delimiter, Italian Excel-friendly): `/api/export/clients.csv`, `/api/export/offers.csv`, `/api/export/commissions.csv`, `/api/export/leads.csv` + Esporta CSV buttons on all 4 list pages
- **WhatsApp click-to-chat**: ClientDetail page shows WhatsApp/Call/Email action buttons with prefilled Italian message via `wa.me/<phone>?text=...`
- **Email mock**: `/api/email/send` logs to `db.email_logs` (NO real delivery — flagged `mocked: true`); `/api/email/logs` for history
- **Digital signature on offers**: react-signature-canvas pad + jsPDF auto-generation of branded PDF (header, items, totals, signature, signer name + date); `POST /api/offers/{id}/sign` stores base64 signature, sets status=accettata, idempotent commission creation
- 100% iteration 3 frontend tests pass; 12/12 P1 backend pytest pass

## Implemented (2026-02-06 — third session)
- **Auth UX hardening**: register form clears demo creds on mode switch, validates password length client-side, shows inline + toast error messages translated to Italian for FastAPI 422 validation errors, auto-seeds demo data for newly registered users
- **File uploads in Documents area**: PDF / Excel / Word / CSV / images / videos (mp4, mov, webm, avi, mkv) up to 50 MB via Emergent Object Storage (`https://integrations.emergentagent.com/objstore/api/v1/storage`)
  - Endpoints: `POST /api/documents/upload` (multipart), `GET /api/documents/{id}/download` (Bearer or `?auth=` query token), `DELETE /api/documents/{id}` (soft-delete `is_deleted=true`)
  - Storage path convention: `agente-crm/uploads/{user_id}/{uuid}.{ext}`
  - UI: drag-and-drop zone, file picker, progress bar, optimistic state updates (no list-refresh races), category filter chips, color-coded file-type icons (PDF=red, Excel=green, Video=violet, Image=orange), file size + date display, download via fetch+blob to preserve auth header
- 11/11 backend tests pass; iter 5 frontend test 100% pass

## Test Credentials
- agente@demo.it / demo1234

## Backlog (P1)
- Email follow-up sender (real SMTP/Resend)
- WhatsApp click-to-chat integration
- Digital signature on offers (PDF + signature pad)
- Offline mode (PWA + IndexedDB sync)
- Real-time map route optimization (visit planner)
- Excel/CSV export for commissions/clients/offers
- Notifications & reminders (browser + email)

## Backlog (P2)
- ERP integration (Fatture in Cloud / TeamSystem)
- Multi-agent / team mode (admin sees all agents)
- Forecasting AI report (PDF export)
- Custom dashboards per mandante
- Audit log
