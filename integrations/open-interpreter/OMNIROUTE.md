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
