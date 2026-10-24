'use strict';

const CACHE_NAME = 'rovor-command-center-shell-v6';
const SHELL = [
  './',
  './index.html',
  './styles.css',
  './reference-hud.css',
  './hud-experience.css',
  './cinematic-layout.css',
  './live-data.js',
  './app.js',
  './reference-hud.js',
  './orbital-earth.js',
  './hud-experience.js',
  './cinematic-layout.js',
  './manifest.webmanifest',
  './hud-icon.svg',
  './rovor-mark.svg',
  './snapshot.json'
];

// Optional on local preview, bundled in published Pages artifact.
const IMAGE_ASSETS = ['./earth-blue-marble.png','./earth-night.png'];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(SHELL).then(() => {
        // Browser Cache objects support add(); older test doubles may only
        // support addAll(). Map assets are optional in local preview.
        if (typeof cache.add !== 'function') return;
        return Promise.allSettled(IMAGE_ASSETS.map(url => cache.add(url)));
      }))
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
  const isShellAsset = /\/(index\.html|styles\.css|reference-hud\.css|hud-experience\.css|cinematic-layout\.css|live-data\.js|reference-hud\.js|orbital-earth\.js|hud-experience\.js|cinematic-layout\.js|app\.js|manifest\.webmanifest|hud-icon\.svg|rovor-mark\.svg|snapshot\.json|)$/.test(path);
  if (!isShellAsset) return;

  event.respondWith(
    fetch(request).then(response => {
      if (response && response.ok) {
        const copy = response.clone();
        // Normalize the cache key: snapshot.json is fetched with cache:'no-store'.
        // A no-store Request can be rejected by Cache.put, so cache by its URL instead.
        caches.open(CACHE_NAME)
          .then(cache => cache.put(new Request(request.url), copy))
          .catch(() => {});
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
