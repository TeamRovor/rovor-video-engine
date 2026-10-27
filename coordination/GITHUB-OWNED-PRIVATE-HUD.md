# ROVOR private HUD — GitHub owns source and releases

**Target:** TeamRovor/rovor-video-engine `main` is the authoritative HUD source. GitHub Actions deploys a private Cloudflare Worker with D1 telemetry. It does **not** require ChatGPT Sites, Codex, or Work credits to edit, review, test, or publish.

## What exists, and what does not

- The GitHub Pages HUD (`teamrovor.github.io/rovor-video-engine/native-v8-9/`) is a **public static preview**. It is NOT an appropriate location for private API keys, employee receipts, or provider-account data.
- The old `rovor-private-hud.*.chatgpt.site` is a **different ChatGPT-hosted Site**. It is not updated by a GitHub merge. Keep it private and untouched until the GitHub-owned deployment is independently working.
- The GitHub-owned private Worker will be a new **hosting origin**, using the original `dashboard/command-center/native-v8-9/` HUD assets and `integrations/hud-cloud/worker.mjs`, not a redesigned website. It uses Cloudflare D1 and separate login and reporter credentials. It does not import or destroy the ChatGPT Site's D1 database or authentication.
- The Cloudflare Worker host and its database may need one-time provisioning; a committed workflow is not proof of a running service or connected reporter.

## Release control

1. Any authorized human or AI worker can propose a branch / pull request against this GitHub repository. The source lives here, not in the ChatGPT Sites editor.
2. `.github/workflows/deploy-private-hud-cloudflare.yml` runs offline auth, UI, and deploy-security tests for PRs. **No deployment secrets are made available to PR code.** Merging a reviewed and passing PR is the normal way to approve changes.
3. Production release from trusted **main only**: go to **GitHub → TeamRovor/rovor-video-engine → Actions → GitHub-owned PRIVATE ROVOR HUD (Cloudflare Worker) → Run workflow**. This manually publishes the merged repo version, with **no ChatGPT Work/Codex credits**. Before changing from manual releases to automatic releases, confirm the private origin, authentic telemetry and D1 backup/recovery.
4. After successful, private, end-to-end verification, a repository administrator may set the **Actions variable** `ROVOR_HUD_GITHUB_AUTO_DEPLOY=enabled`. Every merged, matching HUD source change on main can then trigger a release. It defaults OFF.
5. Set a GitHub environment `rovor-hud-production` with required owner/team reviewers if that GitHub tier supports them. Do not grant arbitrary agents access to production secrets, environment approval, direct main pushes, or manual deployments.
6. Failed safety tests, missing credentials, wrong database ID, untrusted branches, or absent publisher config **fail closed**. No automatic retries of failed provider inference jobs.

## One-time hosting configuration (owner only)

**Cloudflare:** create/reuse a Cloudflare Workers account (verify the free plan and limits), enable its Workers subdomain or approved custom hostname, and create **a dedicated D1** database named `rovor-hud-telemetry`. Do **not** point this workflow at the existing ChatGPT Site's unknown D1. Do not create a public unprotected telemetry page.

**GitHub Actions secrets** in the **same repository**, preferably scoped to the production environment:

- `CLOUDFLARE_API_TOKEN` — token with the minimum necessary Worker and D1 deploy permissions.
- `CLOUDFLARE_ACCOUNT_ID` — exact Cloudflare account ID.
- `ROVOR_HUD_D1_ID` — provisioned Cloudflare D1 database UUID.
- `ROVOR_HUD_READER_TOKEN` — random 32+ character private HUD login credential.
- `ROVOR_HUD_WRITER_TOKEN` — different random 32+ character outbound Mac reporter credential.

**GitHub Actions variable** `ROVOR_HUD_DEPLOY_ORIGIN`: the exact new HTTPS Worker origin (no path/query/hash). It is read back after deployment; release fails unless anonymous viewer and quota asset requests are denied and authenticated original HUD, quota board, and D1 API respond correctly.

Do not paste API keys or tokens into GitHub code, commits, PRs, issues, Pages, workflow inputs, runtime logs, chat messages, or screenshots. Keep all nine OmniRoute provider keys in their existing private provider runtime. The release workflow does **not** provision or invoke paid AI model routes.

## 24/7 telemetry, not fake meters

After the first successful hosted deployment, point the **existing** outbound Mac OmniRoute reporter at the new `ROVOR_HUD_DEPLOY_ORIGIN` and ensure its Keychain service `rovordigital.hud.writer` matches the new worker's writer secret. Use the existing `tools/hud_telemetry_publisher.mjs` and the documented `com.rovor.hud-reporting` LaunchAgent. First validate all three `1h`, `24h`, `7d` ingests and a second report after closing Terminal. This reporter is independent of the UI and cannot dispatch inference.

When the Mac is connected it may report all **nine configured provider slots** with request counts, tokens and receipt-limited worker activity. A **zero** request count is legitimate only if the complete 24h aggregate was freshly measured. Provider **quota percentage / reset time** requires authenticated account-specific quota evidence. A key existing in OmniRoute does **not** mean that all nine providers have measured limits or are simultaneously running; unknown quota rings must remain unfilled.

Cloud Worker and D1 remain remotely accessible when the Mac is off, but readings are marked stale; moving model execution off the Mac requires a **separate** verified, free-only cloud runtime and is not done by this hosting release. Keep STOP and human PASS/FAIL where they are until their separate private runtime is migrated with authenticated receipts and tests.

## The nine AI contributors

Google Gemini, Mistral, NVIDIA NIM, Cohere, SambaNova, Cloudflare Workers AI, Groq, OpenRouter and Hugging Face models can all participate **through the same GitHub contribution path** when the worker invoking each model has an authorized GitHub App/tool and its own least-privilege repo permissions. A provider API key by itself gives **no GitHub access**. Use GitHub issues/tasks to select work, branches for implementation, PRs for review, CI for checks, and main-only deployments. The models should not share an unrestricted production GitHub token or any private HUD login/provider secret.

**Definition of done:** GitHub Action succeeds from main; it reports authenticated private-host readback; Mac reporter continuously delivers fresh snapshots; each of nine distinct configured connections appears with its actual measured request activity; quota rings show real provider limits when available; owner STOP/PASS/FAIL and private receipts are verified separately. The existing ChatGPT Site should not be abandoned or disabled until the replacement has passed those checks.
