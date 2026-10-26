import {handle} from './worker.mjs';

// Deploy only behind the registered Site's owner-private platform access policy.
// Sites verifies browser/MCP identity and service access before invoking this code.
export function createSitesHandler(hudHTML, quotaJS = '') {
  return async (request, env) => {
    const url = new URL(request.url);
    if (url.pathname === '/api/hud/ingest') return handle(request, env);
    const identity = request.headers.get('oai-authenticated-user-id');
    if (!identity || identity.length > 200) {
      return Response.json({error: 'site_identity_required'}, {status: 401, headers: {'Cache-Control': 'no-store'}});
    }
    // The existing quota board is an owner-private static module, not a credential
    // or a new HUD. Never publish it without the same platform viewer identity.
    if (url.pathname === '/hud-quota.js') {
      if (request.method !== 'GET') return Response.json({error: 'method_not_allowed'}, {status: 405});
      if (!quotaJS) return Response.json({error: 'not_found'}, {status: 404});
      return new Response(quotaJS, {headers: {
        'Content-Type': 'text/javascript; charset=utf-8',
        'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'
      }});
    }
    // Viewing uses the platform identity; writer bearer credentials stay separate.
    // The internal per-request reader capability never reaches browser or storage.
    const internalReader = crypto.randomUUID() + crypto.randomUUID();
    const headers = new Headers(request.headers);
    headers.set('Authorization', 'Bearer ' + internalReader);
    if (url.pathname === '/login') return Response.redirect(url.origin + '/', 303);
    const authenticated = new Request(request, {headers});
    const ASSETS = {fetch: async assetRequest => {
      const pathname = new URL(assetRequest.url).pathname;
      if (pathname !== '/' && pathname !== '/index.html') return new Response('Not found', {status: 404});
      return new Response(hudHTML, {headers: {'Content-Type': 'text/html; charset=utf-8'}});
    }};
    return handle(authenticated, {...env, HUD_READER_TOKEN: internalReader, ASSETS});
  };
}
