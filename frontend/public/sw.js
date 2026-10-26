/* Service worker mínimo: solo el shell de la app (nunca datos ni /api).
 * - Navegaciones: red primero; sin red, el index.html guardado (abre la app).
 * - Todo lo demás pasa directo a la red (los /assets ya son inmutables en HTTP).
 * Subir SHELL_VERSION si cambia la lista de archivos del shell. */
const SHELL_VERSION = 'shell-v1';
const SHELL = ['/', '/index.html', '/manifest.json', '/logo192.png', '/logo512.png', '/apple-touch-icon.png'];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(SHELL_VERSION).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== SHELL_VERSION).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET' || request.mode !== 'navigate') return;
  if (new URL(request.url).pathname.startsWith('/api/')) return;
  event.respondWith(
    fetch(request).catch(() => caches.match('/index.html', { cacheName: SHELL_VERSION })),
  );
});
