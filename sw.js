// Service worker for Caderneta de Rendimentos.
// Caches the app shell so it opens instantly (and works offline for anything
// already visited) — bump CACHE_NAME whenever index.html changes meaningfully
// so returning visitors pick up the update instead of a stale cached copy.
const CACHE_NAME = 'caderneta-rendimentos-v6';
const APP_SHELL = [
  './',
  './index.html',
  './manifest.json',
  './icons/icon-192.png',
  './icons/icon-512.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((names) =>
      Promise.all(names.filter((n) => n !== CACHE_NAME).map((n) => caches.delete(n)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Never cache calls to the Banco Central API — that data must always be live.
  if (url.hostname.endsWith('bcb.gov.br')) return;
  // Only handle our own same-origin app-shell requests; let everything else
  // (other origins, non-GET requests) pass straight through to the network.
  if (event.request.method !== 'GET' || url.origin !== self.location.origin) return;

  const isAppShellPage = event.request.mode === 'navigate' || url.pathname.endsWith('.html') || url.pathname.endsWith('/');

  if (isAppShellPage) {
    // Network-first for the app itself: since this is under active
    // development, a returning visitor should always get the latest version
    // when online — the cache only kicks in as an offline fallback.
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          if (response && response.ok) {
            const copy = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
          }
          return response;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  // Cache-first for static assets (icons, manifest) — these change rarely,
  // so it's fine to serve the cached copy instantly and refresh in the background.
  event.respondWith(
    caches.match(event.request).then((cached) => {
      const network = fetch(event.request)
        .then((response) => {
          if (response && response.ok) {
            const copy = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
          }
          return response;
        })
        .catch(() => cached);
      return cached || network;
    })
  );
});
