/* Self-contained exact HUD offline shell. Public/source requests never cached. */
'use strict';
const CACHE='rovor-exact-hud-shell-v4';
const SHELL=['./','./index.html','./style.css','./live-panels.css','./earth-motion.css','./app.js','./live-panels.js','./reference.png','./reference-blue.webp','./manifest.webmanifest'];
self.addEventListener('install',event=>{
  event.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting()));
});
self.addEventListener('activate',event=>{
  event.waitUntil(caches.keys().then(keys=>Promise.all(
    keys.filter(k=>k.startsWith('rovor-exact-hud-shell-')&&k!==CACHE).map(k=>caches.delete(k))
  )).then(()=>self.clients.claim()));
});
self.addEventListener('fetch',event=>{
  const req=event.request;
  if(req.method!=='GET')return;
  const url=new URL(req.url);
  if(url.origin!==self.location.origin)return;
  // The worker is scoped to /exact/. Never intercept GitHub API or pinned raw-data fetches.
  if(!url.pathname.includes('/exact/'))return;
  if(!/\/(?:index\.html|style\.css|live-panels\.css|earth-motion\.css|app\.js|live-panels\.js|reference\.png|reference-blue\.webp|manifest\.webmanifest)?$/.test(url.pathname))return;
  event.respondWith(fetch(req).then(response=>{
    if(response?.ok){const copy=response.clone();caches.open(CACHE).then(c=>c.put(req,copy)).catch(()=>{});}
    return response;
  }).catch(()=>caches.match(req)));
});
