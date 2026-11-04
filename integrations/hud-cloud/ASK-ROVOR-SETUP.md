# Ask ROVOR — private OmniRoute chat

This upgrade is **real chat inference**, not a background employee scheduler. It reuses the original native v8.9 HUD. Cloudflare remains the authenticated browser origin; the Mac initiates every relay connection outbound. No public tunnel, URL-configurable reverse proxy, provider API key in the browser, or paid provider route is added.

## What the UI can prove

- **Received / queued:** a prompt has been stored privately in D1. No inference proven.
- **Claimed:** the Mac bridge accepted that one request. Completion not proven.
- **Complete:** the Mac bridge supplied a nonempty model response. The requested OmniRoute model ID is recorded, but a fallback's ultimate upstream identity is not independently attested.
- **Failed / offline / expired / stopped waiting:** not a verified completion. Stopping waiting on the phone is not a remote cancel, and no automatic inference retry occurs.
- **Cloudflare AI:** separate hosted model path, manually selected. It must never be represented as a call to OmniRoute.

This does **not** implement file edits, employee task dispatch, PASS/FAIL approval, model quotas, model tool calls or background delivery promises.

## Deploy only to the existing GitHub-owned Cloudflare HUD

1. Review and merge the PR into `main`. All PR checks should pass.
2. GitHub → Actions → **GitHub-owned PRIVATE ROVOR HUD (Cloudflare Worker)** → **Run workflow**, branch `main`. This runs the existing fail-closed source checks, applies `CREATE TABLE IF NOT EXISTS` to the existing configured D1, and deploys using existing Cloudflare credentials and private settings.
3. Read the workflow result carefully. A green GitHub run verifies deployed assets/private auth only to the extent of its existing readback checks. It does **not** mean the Mac is online or any model call succeeded.
4. The old ChatGPT-hosted private Site is a different origin, and this workflow does not publish to it. Use the verified Cloudflare HUD origin.

## One Mac setup step (required for OmniRoute, not Cloudflare AI)

The Mac must have the latest merged repo checkout, Node.js, Python 3, running OmniRoute, and both *existing* macOS Keychain credentials:

- `rovordigital.omniroute.endpoint`: local OmniRoute endpoint key.
- `rovordigital.hud.writer`: the same writer credential configured in Cloudflare/GitHub secrets.

From that checkout, run:

```bash
git pull --ff-only
bash tools/install_hud_chat_relay.sh https://rovor-hud-telemetry.rovordigital.workers.dev
```

The installer creates an isolated `com.rovor.hud-chat-relay` LaunchAgent and changes no existing OmniRoute or HUD telemetry LaunchAgent. It does not read or write model API keys outside their existing private OmniRoute runtime.

Verify it is loaded:

```bash
launchctl print gui/$(id -u)/com.rovor.hud-chat-relay
tail -n 30 ~/Library/Logs/rovor-hud-chat-error.log
```

Sign in to the **Cloudflare** HUD, open Ask ROVOR and confirm a nonempty OmniRoute free-route catalog. Send one *non-sensitive* prompt and confirm the request transitions through queued → claimed → complete, with an actual answer. If the Mac is off, model requests do not execute. This bridge deliberately does not make provider inference permanently cloud-hosted.

## Free-only admission

The Mac enumerates the installed OmniRoute catalog but offers only explicitly marked OpenRouter `:free` routes, named ROVOR free combos, and exact model IDs separately verified free and provided via optional `ROVOR_HUD_CHAT_FREE_MODELS` (comma-separated IDs). This explicit configuration is **not** automatically filled from an API key; the owner must verify each provider's free allowance, billing behavior and fallback rules before allowing direct model IDs that do not identify a zero-cost model. A free-named combo also requires verification of its underlying routes before using it. No round robin is introduced.

Enabling every one of the nine providers depends on current account access and a verified compatible model; a configured key is not proof of a usable, zero-cost model. The UI must say offline/unknown rather than invent activity.

## Privacy and retention

Browser conversations are stored in that device's local browser storage; they are not synced between devices. Queued prompt history and completed model replies are temporarily stored in the **private Cloudflare D1** database and cleaned after their retention window by the relay poller. D1 backups may retain copies longer. Do not submit private client content to a free-tier model without explicit client authorization.

Reader and writer bearer credentials are distinct; only the reader can submit and poll, and only the existing Mac writer credential can announce/claim/finish. Neither key is stored in client JavaScript or committed to GitHub. The Mac does not expose OmniRoute on an inbound public port.

## Later: Provider Manager

A future provider-key form should send keys to an authenticated backend with encryption at rest, redacted logs, scoped permissions, rotation and revocation; the keys must never be in localStorage, public Pages or GitHub code. Provider-specific connectors would discover models, determine free/billing eligibility, track usage where APIs support it and refuse unsupported quotas. That is **not included in this PR**.
