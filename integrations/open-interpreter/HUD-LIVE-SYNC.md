# Existing ROVOR HUD — private live OmniRoute connection

Implemented bridge, not yet verified on Amar's Mac. The public GitHub Pages URL cannot reach a private Mac by itself.

Run `sh tools/start_hud_live_sync.sh` from this exact reviewed checkout on the Mac. It verifies an optional temporary Cloudflare tunnel binary against official release SHA256 (2026.10.3); otherwise it reuses installed cloudflared. No paid API calls. Open the single-use private pairing link printed in Terminal on the phone. This serves the **same native v8.9 HUD HTML**, with a scoped live workload adapter. No new HUD design, public hosting replacement, worker scheduler, queue or provider configuration.

The process must stay running on the Mac. Ctrl+C stops the telemetry server/tunnel; the existing ghost worker is unaffected. This is foreground startup, not a launch-at-login service or a permanent domain. Cloudflare's temporary tunnel may disconnect; the HUD then clears live measurements rather than retaining misleading filled bars. Restart to issue a new pairing link. Do not paste the pairing link into public GitHub issues.

## Measured behavior

- Inventory: `/v1/models` from the actual local gateway, as visible to its endpoint key. Exclude combo virtual models. No three-model route filter, no fixed nine-slot assumption. Catalog may contain aliases; IDs are not proof of successful inference.
- Recorded usage: `/api/usage/analytics` with explicit moving UTC start/end boundaries. Refresh requested every five seconds while visible, with overlapping requests deduplicated. Inventory refreshes every minute. The analytics endpoint normally caches by full query for up to 60 seconds; changing exact window boundaries requests a current window without changing gateway settings.
- Bars: measured requests per model divided by the **entire reported request total** for 1h, 24h or 7d. These are REQUEST SHARE bars, not quota-consumption bars or current execution load. Measured request/token counts displayed separately. Unknown unobserved/ambiguous catalog IDs stay null. Upstream returns only its top 50 model rows; partial coverage is labeled. No fabricated remaining quota.
- `/api/usage/quota` is deliberately unused: upstream v3.8.52 can synthesize percentages from queue pressure and may report 100% remaining without a measured allowance. Per-provider allowances, shared pools, reset times and per-employee mapping remain unsupported in this bridge.
- Credentials: the installed OmniRoute CLI's local machine-token helper is used only against fixed `127.0.0.1:20128` read endpoints. Existing endpoint key comes from the process environment or the known Mac Keychain service, never browser JavaScript, a Git commit or the tunnel. Raw upstream payloads never reach the browser; sanitizer only returns model IDs/provider slugs and numeric counts/tokens.
- Access: loopback listener `127.0.0.1:20129`; exact Host allowlist; one-use pairing code passed in a URL fragment then exchanged for an HttpOnly SameSite cookie. Cookie Secure on the HTTPS tunnel; session expires after seven days or process restart. No generic HTTP proxy, filesystem browser, inference endpoint or dispatch controls. Failed source requests return 503, never an old success snapshot.

## Prerequisites and actual host gate

Installed Node with fetch/AbortSignal support, installed OmniRoute v3.8.52-compatible CLI, working gateway on port 20128 and permission to read analytics through local CLI authentication. Inference-only endpoint keys do not themselves grant analytics access. The bridge never disables authentication or broadens key scopes. A real Mac startup must print the live catalog count and measured 24h request count before it prints a private pairing link. Browser checks must then show CONNECTED with matching source counts, followed by DISCONNECTED/empty bars when bridge/gateway stops.

## Validation

`node --test tests/test_hud_omniroute_bridge.mjs`
`node --check dashboard/command-center/native-v8-9/live-omniroute.js`

Tests use a 12-model fixture (not live Mac evidence) and exercise calculations, zero/unknown, duplicate/ambiguous/partial records, polling deduplication, real HTTP pairing, one-use tokens, Host rejection, missing authentication, denied mutation/proxy routes and no stale success on gateway failure.

Upstream contracts reviewed from `cheaper-inference/OmniRoute` release/v3.8.52: `src/app/api/v1/models/route.ts`, `src/app/api/usage/analytics/route.ts`, `src/lib/usage/analyticsResponseCache.ts`, `src/app/api/usage/quota/route.ts`, `bin/cli/utils/cliToken.mjs`. Cloudflare binary provenance: official `cloudflare/cloudflared` release 2026.10.3 API asset digests.

## Connect the existing published HUD URL

The published native HUD now includes a LINK button on Workload Distribution. Paste an unused pairing link from the updated Mac bridge into this form; do not open the private link as a replacement HUD. Pairing exchanges the one-use code for a 24-hour snapshot-only bearer capability. It is kept in this browser tab's sessionStorage and never sent to GitHub; upstream OmniRoute keys remain on the Mac. Reload retains the link in the same tab; Disconnect clears it. The exact allowed viewer Origin is https://teamrovor.github.io. Other Origins, wildcard CORS, arbitrary proxy paths, writes and bearer access to private HTML are denied. Only sanitized snapshot reads are authorized. Expiry or a stopped tunnel clears usage. This is request-share telemetry; real quota and worker attribution remain unavailable.

Previously running bridges must restart on this reviewed source before /pair/external works. Old one-use links cannot be re-used after pairing; restarting creates a fresh link. The public HUD stays at its original address throughout pairing and subsequent refreshes. Browser regression checks cover actual cross-origin pairing/preflight and snapshot reads between two local fixture servers, keeping the viewer at its original origin; no real Mac connection is claimed by those tests.
