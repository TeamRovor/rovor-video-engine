'use strict';

const CACHE_NAME = 'rovor-command-center-shell-v5';
const SHELL = [
  './',
  './index.html',
  './styles.css',
  './live-data.js',
  './app.js',
  './manifest.webmanifest',
  './hud-icon.svg',
  './rovor-mark.svg',
  './snapshot.json'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(SHELL))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys
        .filter(key => key.startsWith('rovor-command-center-shell-') && key !== CACHE_NAME)
        .map(key => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  // Never cache GitHub API/raw data: the dashboard must verify live data online.
  if (url.origin !== self.location.origin) return;

  const path = url.pathname;
  const isShellAsset = /\/(index\.html|styles\.css|live-data\.js|app\.js|manifest\.webmanifest|hud-icon\.svg|rovor-mark\.svg|snapshot\.json|)$/.test(path);
  if (!isShellAsset) return;

  event.respondWith(
    fetch(request).then(async response => {
      if (response && response.ok) {
        const copy = response.clone();
        // Normalize the cache key: snapshot.json is fetched with cache:'no-store'.
        // Await the write so the service worker cannot be terminated before it finishes.
        try {
          const cache = await caches.open(CACHE_NAME);
          await cache.put(new Request(request.url), copy);
        } catch (_) { /* A cache write failure must not block the live response. */ }
      }
      return response;
    }).catch(async () => {
      const cached = await caches.match(new Request(request.url));
      if (cached) return cached;
      if (request.mode === 'navigate') {
        return (await caches.match('./index.html')) || Response.error();
      }
      return Response.error();
    })
  );
});
