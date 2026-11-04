# Ask ROVOR — verified private OmniRoute chat

## Supported clients and limits

The existing GitHub-owned private Cloudflare HUD serves the same authenticated Ask ROVOR interface on modern iPhone/iPad browsers, macOS browsers and Windows browsers. It adapts phone layouts to full screen, keeps desktop history in a side rail, provides touch and keyboard controls, and does not require installing OmniRoute on the viewing device. Conversation history currently stays **on each device**; there is no cross-device chat-history synchronization.

The browser asks the private Cloudflare Worker to queue a bounded prompt. The existing Mac, while powered on, runs an **outbound-only** relay that checks the private queue and calls its locally authenticated OmniRoute endpoint. The cloud origin never needs a public Mac port, arbitrary forwarding route, or provider API keys in JavaScript. If the Mac relay is offline, the HUD must say **offline**, not act as though prompts were sent.

A chat request is **not** an employee task. Queued means the Cloudflare D1 record exists; running means the Mac claimed it; complete means the Mac submitted a model reply. Claims, chats and model text do not prove employee dispatch. The model label is the *requested* route, not a separately verified upstream model identity. There is no autonomous work scheduler in this feature. Cloudflare Workers AI remains a separate, explicitly labeled selectable backend; it does not mean OmniRoute is connected.

## Owner release: Cloudflare HUD, not ChatGPT Site

Review and merge this PR to `main`. In the GitHub Actions tab run **GitHub-owned PRIVATE ROVOR HUD (Cloudflare Worker)** on `main`. It applies forward-only `CREATE TABLE IF NOT EXISTS` private chat tables, publishes the tracked HUD assets, and verifies private origin and telemetry. The GitHub-hosted public Pages HUD and the old `rovor-private-hud.*.chatgpt.site` are **different sites**. Running the Cloudflare workflow will not update the ChatGPT Site; don't use the public Pages preview for private prompts.

Keep `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `ROVOR_HUD_D1_ID`, `ROVOR_HUD_READER_TOKEN`, `ROVOR_HUD_WRITER_TOKEN` private in the trusted GitHub `rovor-hud-production` environment. Use the existing configured `ROVOR_HUD_DEPLOY_ORIGIN` variable. Never paste API keys into the browser, commits, workflow inputs, or chat.

## Mac bridge (requires one-time owner setup)

Check that Node 24+, OmniRoute and the two **existing** Keychain services are available on the Mac:

```sh
node --version
security find-generic-password -s rovordigital.hud.writer >/dev/null && echo "HUD writer credential exists"
security find-generic-password -s rovordigital.omniroute.endpoint >/dev/null && echo "OmniRoute endpoint credential exists"
```

Use the merged GitHub source in an existing persistent checkout:

```sh
cd /absolute/path/to/rovor-video-engine
ROVOR_HUD_ORIGIN='https://YOUR-AUTHENTICATED-CLOUDFLARE-HUD-ORIGIN' node tools/hud_chat_relay_client.mjs
```

The script loads keys from the Mac's Keychain and contacts **only** the configured private HTTPS origin and local OmniRoute. It does not log prompts or secrets. It must remain running to take queued prompts. The initial route list includes explicit `:free` model identities only; other provider or combo IDs require an **owner-reviewed, actually-zero-cost, current** allowlist. An OmniRoute connection does not prove a model works or is available free. Use a known free-only combo only after independently checking its constituent routes.

For persistent operation copy `integrations/hud-cloud/ask-rovor-launchagent.plist.example` to `~/Library/LaunchAgents/com.rovor.ask-rovor-relay.plist`, set its two absolute paths and exact private Cloudflare origin. Optionally supply a comma-separated list of **verified, approved free** exact model IDs in `ROVOR_HUD_CHAT_FREE_MODELS`. Never place secrets in the plist. Validate and activate:

```sh
plutil -lint "$HOME/Library/LaunchAgents/com.rovor.ask-rovor-relay.plist"
launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.rovor.ask-rovor-relay.plist"
launchctl print "gui/$(id -u)/com.rovor.ask-rovor-relay"
```

For an already installed service, use `launchctl kickstart -k gui/$(id -u)/com.rovor.ask-rovor-relay`; don't bootstrap a duplicate. To roll back: `launchctl bootout gui/$(id -u)/com.rovor.ask-rovor-relay`. This is **separate** from the telemetry publisher or ghost employee scheduler. You do not need a Mac app on iPhone, iPad or Windows.

## Proof before calling it operational

1. CI passes authenticated owner/writer separation, prompt expiration, model allowlist, front-end checks and existing HUD tests.
2. Workflow reports a successful deployment/readback of the actual protected Cloudflare origin, not only a green build.
3. With relay stopped, Ask ROVOR shows OmniRoute offline and does not claim inference.
4. With relay online, a selected verified free model gives a real answer. Check **queued → claimed → complete** in the private HUD. Test a failed call too.
5. Recheck iPhone portrait/landscape, iPad portrait/landscape, macOS and Windows browser sizes and keyboard/touch behavior. Passing mocked browser tests isn't proof of actual Safari hardware testing.

The new cron only removes expired private prompt/result rows. It does not create or dispatch model jobs or paid inference. Chat context stays private to this authenticated worker, and completed prompts are cleared from the private table. Responses are short-lived in private D1; local conversation history remains on each viewer device.
