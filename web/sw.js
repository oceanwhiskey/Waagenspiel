// Offline-Speicher: zuerst das Netz (immer die neueste Version), sonst der Speicher.
// Nur die Dateien des Spiels selbst; alles andere auf derselben Seite (z. B. Noten,
// Musik) geht unberuehrt am Service Worker vorbei.
const CACHE = "waagenspiel-v2";
const FILES = [
  "./", "index.html", "spiel.css", "spiel.js", "figuren.js", "oberflaeche.js", "raetsel.json",
  "manifest.webmanifest", "icon.svg", "icon-192.png", "icon-512.png", "icon-180.png",
];
const BASE = new URL("./", self.location).href;
const GAME_URLS = new Set(FILES.map((file) => new URL(file, BASE).href));

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(FILES)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k.startsWith("waagenspiel-") && k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  url.search = "";
  if (event.request.method !== "GET" || !GAME_URLS.has(url.href)) return;
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        const copy = response.clone();
        if (response.ok) caches.open(CACHE).then((cache) => cache.put(event.request, copy));
        return response;
      })
      .catch(() => caches.match(event.request, { ignoreSearch: true })),
  );
});
