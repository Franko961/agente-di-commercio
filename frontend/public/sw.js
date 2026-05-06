/* AGENTE Gestionale - Service Worker v3 (read-only offline + always-fresh app shell) */
const CACHE_VERSION = 'agente-v3';
const STATIC_CACHE = `${CACHE_VERSION}-static`;
const API_CACHE = `${CACHE_VERSION}-api`;

const STATIC_FILES = ['/manifest.json'];

const CACHEABLE_API_PATHS = [
  '/api/clients',
  '/api/appointments',
  '/api/offers',
  '/api/commissions',
  '/api/mandanti',
  '/api/products',
  '/api/leads',
  '/api/documents',
  '/api/automations',
  '/api/dashboard/stats',
  '/api/auth/me',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((c) => c.addAll(STATIC_FILES)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => !k.startsWith(CACHE_VERSION)).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

function isCacheableApi(url) {
  return CACHEABLE_API_PATHS.some((p) => url.pathname.endsWith(p) || url.pathname.includes(p + '?') || url.pathname.includes(p + '/'));
}

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);

  // Same-origin: network-first so users always get the latest app shell
  if (url.origin === self.location.origin) {
    event.respondWith(
      fetch(req).then((res) => {
        if (res.ok) {
          const copy = res.clone();
          caches.open(STATIC_CACHE).then((c) => c.put(req, copy)).catch(() => {});
        }
        return res;
      }).catch(() => caches.match(req).then((cached) => cached || caches.match('/manifest.json')))
    );
    return;
  }

  // API requests -> network-first with fallback to cache (read-only offline)
  if (isCacheableApi(url)) {
    event.respondWith(
      fetch(req).then((res) => {
        if (res.ok) {
          const copy = res.clone();
          caches.open(API_CACHE).then((c) => c.put(req, copy)).catch(() => {});
        }
        return res;
      }).catch(() => caches.match(req).then((cached) => cached || new Response(JSON.stringify({ offline: true, error: 'No cached data' }), { status: 503, headers: { 'Content-Type': 'application/json' } })))
    );
  }
});
