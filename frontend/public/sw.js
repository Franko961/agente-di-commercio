/* AGENTE Gestionale - Service Worker (read-only offline) */
const CACHE_VERSION = 'agente-v1';
const STATIC_CACHE = `${CACHE_VERSION}-static`;
const API_CACHE = `${CACHE_VERSION}-api`;

// Static shell to pre-cache
const STATIC_FILES = ['/', '/manifest.json'];

// API GETs we cache (read-only offline data)
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
    caches.open(STATIC_CACHE).then((cache) => cache.addAll(STATIC_FILES)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => !k.startsWith(CACHE_VERSION)).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

function isCacheableApi(url) {
  return CACHEABLE_API_PATHS.some((p) => url.pathname.endsWith(p) || url.pathname.includes(p + '?') || url.pathname.includes(p + '/'));
}

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);

  // Same-origin static -> cache-first
  if (url.origin === self.location.origin) {
    event.respondWith(
      caches.match(req).then((cached) => cached || fetch(req).then((res) => {
        const copy = res.clone();
        caches.open(STATIC_CACHE).then((c) => c.put(req, copy)).catch(() => {});
        return res;
      }).catch(() => caches.match('/')))
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
