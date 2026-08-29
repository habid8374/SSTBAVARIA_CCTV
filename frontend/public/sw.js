const CACHE_NAME = "sstbavaria-cctv-v1";
const APP_SHELL = [
  "/login",
  "/manifest.json",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(APP_SHELL))
      .catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

// Estrategia stale-while-revalidate solo para recursos propios (páginas y
// estáticos de Next.js). Las llamadas al backend (otro origen, Railway)
// pasan de largo sin tocar el cache: los datos de cámaras/eventos deben
// verse siempre frescos, nunca servidos desde acá.
self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  event.respondWith(
    caches.match(request).then((cached) => {
      const enRed = fetch(request)
        .then((response) => {
          if (response.ok) {
            const copia = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, copia));
          }
          return response;
        })
        .catch(() => cached);
      return cached || enRed;
    })
  );
});
