/* Scoped to /exact/: never cache Github API/source data. */
'use strict';
const CACHE='rovor-exact-hud-shell-v1';
const SHELL=['./','./index.html','./style.css','./app.js','./reference.png','./reference-blue.webp','./manifest.webmanifest'];
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting())));
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('rovor-exact-hud-shell-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',event=>{
  const req=event.request;
  if(req.method!=='GET'||new URL(req.url).origin!==self.location.origin) return;
  const url=new URL(req.url);
  const local=url.pathname.match(/\/(index\.html|style\.css|app\.js|reference\.png|reference-blue\.webp|manifest\.webmanifest|)$/);
  if(!local)return;
  event.respondWith(caches.match(req).then(hit=>hit||fetch(req)));
});
