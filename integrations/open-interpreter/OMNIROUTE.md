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

**Status in PR #35:** discovery and runbook added. No OmniRoute package, service, provider account, API key, model switch or Mac integration was installed from GitHub. 
