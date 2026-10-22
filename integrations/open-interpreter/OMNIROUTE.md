# OmniRoute — optional local AI provider gateway

Source: https://github.com/cheaper-inference/OmniRoute (repository default branch at inspection: `release/v3.8.53`).
Purpose: consolidate **separately eligible** third-party AI provider accounts behind a local OpenAI-compatible API. This is not an AI model and **does not give ROVOR free credits**. The published pool totals represent quotas controlled by outside providers, potentially with region, identity, tool-use and terms restrictions. Quotas and policies may change.

## Compatibility boundary

- OmniRoute's CLI tools catalog lists **Open Interpreter** as a supported OpenAI-compatible client.
- Its documented `omniroute run <target>` launcher explicitly targets **claude, codex, aider, goose, opencode, qwen and gemini**; **do not assume `omniroute run interpreter` exists**.
- ROVOR's observed `interpreter` is `v0.0.56` and uses `~/.openinterpreter/config.toml` plus project overrides. Actual custom-provider syntax, authentication, responses/tool-calling behavior and model identity must be verified on the Mac; don't copy native Codex settings into Open Interpreter as if identical.
- OmniRoute can proxy `/v1/chat/completions` and `/v1/responses` with an authenticated localhost API at `http://127.0.0.1:20128/v1`, **if** a valid route is configured.

## Opt-in Mac preparation (separate from the current ChatGPT-login session)

1. Inspect the upstream install package, its npm scripts/dependencies, and Node runtime suitability; then, if acceptable, install the official `omniroute` package:
   ```sh
   node --version
   npm view omniroute version
   npm install -g omniroute
   ```
   The upstream docs note that npm 11 may block install scripts required for some components. Review any script permission prompts; don't blanket-disable protections or auto-approve unknown scripts.
   **Intel Mac installation issue observed Oct 22, 2026:** npm 11.19.1 / Node 24.22.0 reached dependency warnings, but `npm install -g omniroute` failed with `EACCES: permission denied, mkdir '/usr/local/lib/node_modules/omniroute'`. This is a global npm prefix permission failure, not an AI-provider issue. **Do not use sudo or change ownership of /usr/local**. Instead try a per-user global prefix, with the npm 11 approved script list documented upstream (review scripts before approving):

   ```sh
   npm install -g --prefix "$HOME/.local" --allow-scripts=omniroute,keytar,onnxruntime-node,@parcel/watcher,@swc/core,protobufjs,esbuild omniroute
   rehash
   command -v omniroute
   omniroute --version
   ```

   On the user's Mac `$HOME/.local/bin` is already on PATH. The install-with-prefix workaround is **proposed, not yet verified** by a follow-up Terminal log. `ERESOLVE overriding peer dependency` warnings were not the fatal cause. If installation succeeds, run `omniroute`, then verify service health and provider eligibility before trying any model route. A browser tab at localhost:20128 is not proof that the server is running.

2. Start the gateway in a separate Terminal window:
   ```sh
   omniroute
   ```
   Open its local dashboard, complete `omniroute setup` only when needed, and connect an account with an **explicitly eligible free tier** or authorized local model. Keep provider credentials in the gateway/keychain, never in ROVOR's GitHub files.
3. Use `omniroute doctor` and the dashboard's Endpoints page to confirm service readiness and create a scoped OmniRoute key. Test the endpoint locally with a narrowly scoped inexpensive/free model, not a coding agent running autonomously.
4. Only after endpoint and model test, use Open Interpreter's `/model` and supported provider configuration to create a separate **opt-in** route. Leave existing ChatGPT sign-in intact as fallback until provider/tool calling is verified.
5. Compare a small read-only tool task against the default provider. Record accuracy, price (if any), context limits, and failure behavior. Don't enable paid fallbacks automatically.

## Minimum gates before use

- Model and API compatibility verified specifically against Open Interpreter v0.0.56.
- Free provider's acceptable-use terms permit use by this client, at the needed rate.
- No implicit paid fallback or signup-credit dependency.
- Proxy bound to loopback only, with endpoint credential and protected config.
- Sensitive client media/files or business messages are not sent to unknown external models without explicit authorization.
- No provider keys in CLI arguments, logs, Git commits or screenshots.
- Never assume an OmniRoute model preserves an OpenAI ChatGPT subscription's tool access, usage quota, or privileges.

**Status:** the runbook was merged to `main` in PR #35. GitHub does not install local software; Mac installation initially failed with EACCES and is pending per-user-prefix retest. No provider account, API key, model switch or runtime integration is verified. 

## Model catalog HTTP 401 after successful `omniroute connect` (Intel Mac, Oct 22 2026)

Observed: `omniroute connect http://127.0.0.1:20128 --scope read` successfully created a **management** context/token, but `omniroute models` continued reporting `Model request failed (HTTP 401)`. This is not evidence the server or upstream provider keys are broken. In OmniRoute's current source, `bin/cli/commands/model-api.mjs` calls `/api/v1/models`, and `src/app/api/v1/models/catalogRequest.ts` accepts a valid **inference endpoint API key** or dashboard session cookie for the catalog. It does not explicitly accept the scoped management token minted by `omniroute connect`. This can cause a management token to be rejected as an invalid inference key even though the management connection succeeded.

Non-destructive verification:

1. In the logged-in dashboard, open **Endpoints** and create a dedicated limited-scope **inference API key** for local ROVOR testing. **Never put the key in GitHub/chat**, a CLI argument, shell history, or screenshots.
2. In a fresh macOS zsh tab, enter below; paste the key only when the hidden prompt appears. This uses the default local context instead of the active read-token context, without changing saved contexts:

   ```sh
   printf 'Paste the local OmniRoute ENDPOINT key (hidden): '
   read -rs OMNIROUTE_API_KEY; echo
   export OMNIROUTE_API_KEY
   omniroute models --context default
   unset OMNIROUTE_API_KEY
   ```

   No model inference is performed by a model-catalog list. If the key is accepted, capture only the model names and safe metadata. If it still returns HTTP 401, verify the copied **endpoint inference key** and dashboard catalog-auth settings without weakening authentication; test provider connections in the dashboard. `omniroute contexts use default` is also available, but it changes the active context, so prefer per-command `--context default` here.
3. A `401` on `GET /v1/models` does NOT prove the inference service requires a key; the `REQUIRE_API_KEY` setting separately controls POST inference requests. Never disable auth just to make a model list work, particularly when the server has previously warned about listening on `0.0.0.0` with no key requirement. Bind to `OMNIROUTE_SERVER_HOST=127.0.0.1` on the Mac; enforce authentication before future LAN sharing with the Windows laptop.

**Status:** the CLI workaround is based on reviewed source code and is awaiting the user's Mac verification. Do not claim models/providers pass tool calls yet.

