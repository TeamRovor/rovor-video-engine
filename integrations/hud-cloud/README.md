# Persistent private HUD reporting

## Cloud completions in the existing Pages HUD

The GitHub Pages release now builds a sanitized cloud-activity feed and adds a
small module hook to a copied publication artifact. The original native-v8-9
source HTML, logo, orientation rules and panel structure are untouched. Cloud
entries appear in the existing Recent Activity scroll area and its drawer.
They say **recorded completion**, with the latest saved owner review if available; they never
claim a currently online employee or measured OmniRoute usage.

Receipt source files live under `coordination/cloud-shifts/`. Before
publication, the release validates the bounded schema and reads back the
referenced merged result or open reviewable PR head, exact commit and successful CI result on that
source revision. These checks establish the public GitHub result, not the
underlying model, private prompts, or human acceptance. The first Walter
receipt was separately matched to the platform's recorded completed shift.

Future reporting should inspect a **previously completed** cloud run and match
its recorded result to fresh GitHub evidence. Do not mark the currently
executing reporting run completed. Publish a new immutable `<role>-pr<number>.json`
using the exact fields in the first receipt, and add that specific new file to
the reporting task's canonical scopes before writing it. Keep model/tokens
null and human_review `not_recorded`: this feed does not provide those receipts.
Never commit conversation IDs, prompts, credentials, private client work or
raw automation output. Skip a record when runtime provenance or evidence is
unavailable. Existing receipt IDs must not be reused for unrelated work.

The Pages workflow watches new receipt files, so publishing a verified record
does not depend on an open HUD or an awake Mac. The open HUD reads the static
feed once per minute and pauses while hidden. The feed contains at most 200
recent records; source parsing is bounded at 1,000 files. This is a completion
ledger, not live in-progress tracking or cloud model dispatch.
It does not activate the separate unpublished private Site or migrate the nine
provider keys. The existing public Pages HUD exposes only these sanitized
public repository completion records.

## Saved owner PASS / FAIL

Recent Activity opens result cards with PASS and FAIL links. These open a native
GitHub confirmation, binding the decision to the receipt and exact output commit.
Amar must submit while signed in as TeamRovor. The issue and optional reason are
public. Clicking a link alone never saves or claims approval. The issues-opened
workflow accepts only that account's original issue event, writes an immutable
`coordination/cloud-reviews/issue-N.json`, then invokes the existing Pages release
at the actual saved commit. This explicit call avoids depending on a workflow
token push to trigger another workflow. All existing release gates remain.

New reviews supersede older decisions for that output. Editing or closing an
old issue does not change its recorded decision. Employees must never submit
owner reviews or write this ledger. FAIL requests a new linked bounded rework
task; it does not replay an old job. PASS does not deploy or execute output.
Keep reviewable output commits immutable: make revisions in a new linked PR and
receipt, rather than replacing an already reviewed head. Account authentication
is not a hardware-backed proof of who operated that account.

The built-in Mac observation is archived. Unless the actual live adapter reports
CONNECTED, the workload summary labels Mac telemetry disconnected and points to
recorded cloud completions. Feed fetch time, publication time and task completion
time remain distinct. No static completion record proves someone is working now.
The first real owner submission and its complete deployed readback still require
runtime verification; tests do not stand in for Amar's decision.

## Connected private Sites deployment

The registered owner-private target is `appgprj_6add1e2cc8c08191839344b34d7dbf50`.
Reuse this identity; it has no published version yet. Do not create another Site.
Source upload currently fails because the managed execution environment cannot
resolve the registered hosting Git server. Native publication requires a real
source push; do not substitute the GitHub implementation commit as a Site
source commit.

`sites-adapter.mjs` delegates to the existing receiver behind Sites' private
access boundary. Browser/MCP readers require platform-supplied user identity;
they do not enter or save a second HUD viewing key. Model/worker uploads still
require the separate writer credential. The adapter is only appropriate while
the Site remains owner-private, with Sites dispatch in front of it.

From the implementation repository, prepare the existing registered Site checkout:

```
node integrations/hud-cloud/build-sites.mjs /absolute/path/to/registered-site-checkout
```

The builder embeds the original native-v8-9 HUD and the existing receiver into
one dependency-free ESM Worker. It preserves the Site ID, declares `DB` and
MCP, and writes the first schema-only migration plus its journal. Rebuilding
is deterministic; conflicting existing migrations stop the build before files
are changed. Local tests verify this source/build behavior; the binding and
migration still require validation by a real Sites deployment.

When source synchronization works, use the Sites source workflow to push and
package these exact files, then publish the resulting exact source commit and
archive through owner-private deployment. Configure `HUD_WRITER_TOKEN` as a
runtime secret before publishing; a second reader key is unnecessary in this
platform-specific variant. Check the deployed D1 schema, owner sign-in,
anonymous denial and authenticated uploads before installing the Mac reporter.

For this private target the reporter also needs the Site's supported service
access credential. Keep it in Keychain as `rovordigital.hud.service` (or the
controlled environment variable `ROVOR_HUD_SERVICE_TOKEN`). It is sent only to
the configured Site origin as `OAI-Sites-Authorization`; normal writer
authentication uses the separate `Authorization` header. Redirects remain
disabled. Never publish the origin credential in code, a plist or logs. Platform
service access must not be replaced by making the Site public.

With `mcp` declared, Sites can provision its own reader plugin on publication.
Verify the actual connection before claiming ChatGPT can read status by name.
No plugin has been provisioned or connected by this local build.

Private-Sites checks: `node --test tests/test_hud_cloud.mjs tests/test_hud_sites.mjs`
runs 29 tests, including original-HUD byte preservation in the response,
platform identity/read permissions, upload isolation, MCP, deterministic bundle
import, immutable migration handling and separate service authentication.

## Standalone Cloudflare variant

Status: implemented and locally tested, **not deployed, not installed on Mac,
not connected as a ChatGPT tool**. No cloud account credentials were available
in this session. The current temporary tunnel is not converted merely by
merging this code.

The existing HUD is served unchanged behind a fixed HTTPS origin and private
device sign-in. A separately running outbound reporter uses the existing
OmniRoute model collector and employee SQLite reader, sending the 1h/24h/7d
aggregates to this cloud receiver. Closing the HUD does not stop reporting.
No tunnel URL, one-use pairing link, inbound Mac port, inference call or worker
dispatch is involved. The root response adds the existing live-adapter start
hook and removes the temporary-link button; existing source HTML is untouched.

The receiver stores the latest report for each period in D1. It also retains
one 24h-aggregate snapshot per minute for the preceding day, up to 32 KiB each.
This is sampled history, not a complete per-request event log. History reads
return at most 120 recent snapshots. Verified OmniRoute cached provider limits (including units and reset dates) now survive the outbound reporter and private receiver. Only recent, provider/account-matched cache records create bars; expired reset windows, forged percentages and missing limits never create filled meters. These remain provider-reported cache values, not proof of a free request or successful inference. Unknown quotas and upstream-model
attribution remain unknown. No prompts, draft outputs, private paths, provider
credentials or raw payloads are copied. Titles come from the existing public
queue-based employee reader, and only explicit telemetry fields are retained.

Every report retains its source observation time. Duplicate/older uploads
cannot overwrite new data or refresh the original receipt time. Browser meters
keep the existing 15-second freshness threshold; `/api/hud/status` returns
`fresh`, `stale`, or `never_received`. Reports do not prove human approval or
that each employee is online. Worker heartbeat and employee evidence stay
separate. When the Mac is asleep/offline, the cloud reader remains available
with old reports marked stale. Running OmniRoute while the Mac is off is a
separate hosting migration, not something this transport provides.

## Deployment boundary

Use an authenticated Cloudflare account and verify its $0 plan/allowance before
deployment. No paid plan or inference provider is selected by this source.
The supplied configuration deliberately has a placeholder database ID.

From this directory, using the account's approved installed Wrangler:

1. Provision D1 `rovor-hud-telemetry`, replace only `database_id` in
   `wrangler.jsonc`, and apply `schema.sql` to that database.
2. Configure two **different**, independently generated random secrets of at
   least 32 characters as `HUD_WRITER_TOKEN` and `HUD_READER_TOKEN` through the
   provider's secret mechanism. Never put them in source or GitHub logs.
3. Deploy this Worker with its D1 and ASSETS bindings. ASSETS points to the
   existing native-v8-9 HUD, so no HUD redesign or source-copy fork is needed.
   `run_worker_first` ensures all assets pass through private authentication.
4. Verify anonymous root redirects to `/login`, anonymous API access returns
   401, writer credentials cannot read, and reader credentials cannot upload.
   The sign-in form exchanges the reader key for a Secure/HttpOnly/SameSite
   cookie lasting seven days. It works independently on each device; there
   are no keys in URLs, browser storage, or embedded HUD JavaScript. Rotate
   the reader secret to revoke existing device cookies.

## Permanent Mac reporting

Use a persistent reviewed repository checkout, not a temporary download.
The reporter imports the existing bridge and its Python employee reader, so
the checkout must contain `tools/hud_omniroute_bridge.mjs`,
`tools/hud_employee_snapshot.py`, `tools/omniroute_ops_snapshot.py`, and the
public `coordination/tasks.json`. Existing worker services remain untouched.

Store the writer key in macOS Keychain under service `rovordigital.hud.writer`
using the account's secure credential-entry flow. The reporter reads that key
and the existing OmniRoute endpoint key locally; it never uploads either
OmniRoute key. `ROVOR_HUD_WRITER_TOKEN` is supported for controlled test/service
environments but should not be pasted into shell history or a tracked plist.
The origin is configured separately as `ROVOR_HUD_ORIGIN`.

First run `node tools/hud_telemetry_publisher.mjs --once` with that origin.
Only after all three periods are received, populate the three placeholder
paths/origin in `launchagent.plist.example`, install it as the dedicated
`com.rovor.hud-reporting` LaunchAgent, and verify a second report after closing
Terminal. This reports telemetry only; it is not a second workforce scheduler.
Stop/remove only that label to roll back reporting. The reporter repeats with
a 10-second pause, backs off on failures up to five minutes, prevents overlapping
cycles, and does not replay jobs. Slow/unavailable collection can make reports
stale, and unavailable cloud delivery does not produce fake progress. It does
not buffer a complete offline request ledger or prevent Mac sleep.

## ChatGPT without pasted links

`POST /mcp` provides one read-only tool: `rovor_workforce_status`. The reader
credential authenticates it; the writer credential does not. It returns the
latest stored report and explicit freshness. It cannot run jobs or mark work
approved. A connector must be registered against the deployed fixed `/mcp`
endpoint and authenticated **once** before new chats can call it by name.
Source code alone does not install that connector or give every chat access.
Browser device cookies do not grant access to MCP POST requests.

## Verification

`node --test tests/test_hud_cloud.mjs` (from repository root) runs 18 focused
tests on Node 24, using real in-memory SQLite behind a D1-shaped adapter.
Tests cover role separation, device sign-in, original-HUD injection, all periods,
source clocks, duplicate/out-of-order uploads, retained stale reports, retention,
allowlisted fields, malformed payloads, bounded bodies, read-only MCP and the
outbound publisher. These tests do not prove a deployed D1 binding, browser
layout, live gateway delivery, launchd startup, or a completed 24h soak.

Live read-only host evidence collected during implementation: heartbeat was
recent but dispatch reported `failure_circuit_requires_review`; no employee's
`online_verified` was true. That observation is time-specific and is not a
cloud telemetry verification.
