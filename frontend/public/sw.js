const CACHE_NAME = "sstbavaria-cctv-v2";
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

// Notificación push (Web Push + VAPID) — se muestra aunque la app esté
// cerrada; el payload lo arma core/push.py con {titulo, cuerpo, url}.
self.addEventListener("push", (event) => {
  let datos = { titulo: "SST Bavaria — Cámaras IA", cuerpo: "Tienes algo pendiente por revisar.", url: "/dashboard" };
  try {
    if (event.data) datos = { ...datos, ...event.data.json() };
  } catch {
    // payload no era JSON — se usa el texto plano como cuerpo
    if (event.data) datos.cuerpo = event.data.text();
  }

  event.waitUntil(
    self.registration.showNotification(datos.titulo, {
      body: datos.cuerpo,
      icon: "/icons/icon-192.png",
      badge: "/icons/icon-192.png",
      data: { url: datos.url },
    })
  );
});

// Al tocar la notificación: si ya hay una pestaña de la app abierta, la
// enfoca y la manda a la sección correspondiente; si no, abre una nueva.
self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = event.notification.data && event.notification.data.url ? event.notification.data.url : "/dashboard";

  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((listaClientes) => {
      for (const cliente of listaClientes) {
        if ("focus" in cliente) {
          cliente.navigate(url);
          return cliente.focus();
        }
      }
      return self.clients.openWindow(url);
    })
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
