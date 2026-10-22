# Open Interpreter-first Final Cut Pro connection (Jane)

**Primary local executor: Open Interpreter.** Codex is an optional fallback client, not the ROVOR workforce's primary runtime. Walter coordinates Jane and other existing specialist roles, Open Interpreter supplies local agent sessions/MCP/tool permissions, and GitHub holds source/version/task evidence. None of this alone starts an always-on process or tunnels cloud ChatGPT to the Mac.

## Mac proof: Open Interpreter MCP CONNECTED — 2026-10-22

**Do not repeat setup, wheel repair, FCP DTD validation, stage generation, CLI registration, or app-server connection tests on this Mac. These gates passed.** The owner supplied the final Mac stdout from `tools/fcp_interpreter_appserver_smoke.py`, using the existing disposable `~/Documents/Rovor/fcp-interpreter-stage-20261022-160459`. The complete end-to-end, **locally executed** Open Interpreter app-server → third-party FCP MCP test returned:

- `status=passed_interpreter_appserver_mcp_tool_call`, `open_interpreter_connected=true`, `server=fcpxml`;
- **actual tool invocations** `mcpServer/tool/call` of `inspect` succeeded on synthetic `1920x1080 @ 60fps` and `1080x1920 @ 60fps`;
- `outside_root_refused=true` on synthetic sentinel outside `FCP_PROJECTS_DIRS`;
- response digest landscape `917fa862ee2bf2da8fcfa882caf2fa4a322d239ae2e8f69db0a07799148ceb05`; portrait `c27ce12aa10bb336dd916c5f59520f1c0da8e787b86820af1a58a5b874ee1f3b`;
- `native_final_cut_operated=false`, `model_turn_started=false`, `media_modified=false`.

**Established:** Open Interpreter v0.0.56 talks to pinned FCP MCP v0.27.2 on the user's Intel Mac through its own app-server, with a real read-only tool response and denied unsafe test path. This is more than just registering an MCP server; it is **host-verified client MCP communication**. It does NOT show control of the native Final Cut Pro application, FCPXML GUI import, interactive editing, export, background service or agent execution of a model-originated tool call.

**Current actionable next gate:** native Final Cut Pro integration with a **brand-new, isolated, empty test library** and a DTD-validated synthetic FCPXML import candidate. Do not open any existing media, projects, libraries or original ROVOR recordings; do not enable edit/generate/publish tools yet. For the initial import gate, use a controlled operator-approved GUI import into the new test library; separately observe native app effects and save a result record. Do not claim native editing from FCPXML inspection alone.

**Related independently executed Intel CI:** [run 39858034351](https://github.com/TeamRovor/rovor-video-engine/actions/runs/39858034351) passed equivalent app-server real MCP calls without inference. Source: `tools/fcp_interpreter_appserver_smoke.py`.

> **Legacy procedures below are retained as history of earlier setup gates.** "Not verified" statements about the local MCP connection in these historical sections were accurate *at that earlier stage* but are superseded by the Mac proof above. Do not direct anyone to rerun those gates unless a new Mac, changed installed versions or regression failure requires it.

## Sources and supported commands (reviewed 2026-10-22)

- [Open Interpreter MCP](https://github.com/openinterpreter/openinterpreter/blob/main/docs/mcp.md): project or user configurations under [mcp_servers.*], CLI commands interpreter mcp list/get/add/remove, in-TUI /mcp and /mcp verbose. Supports enabled_tools, default_tools_approval_mode, enabled and required. A registered server is NOT a connected server.
- [Configuration](https://github.com/openinterpreter/openinterpreter/blob/main/docs/config.md): trusted project settings in .openinterpreter/config.toml, a DIFFERENT file from .codex/config.toml; /debug-config shows loaded layers.
- [CLI reference](https://github.com/openinterpreter/openinterpreter/blob/main/docs/cli-reference.md): interpreter foreground, interpreter exec for one-off noninteractive tasks, interpreter mcp, interpreter mcp-server, and interactive sessions. Do not assume local command works before running it.
- [Daemon documentation](https://www.openinterpreter.com/docs/terminal/daemon): normal foreground operation does not require a daemon; shared background daemon is optional. But the user's Intel Mac v0.0.56 had a persistent package/platform mismatch on daemon start. Foreground agent/skills/MCP still need separate proof.
- [Third-party FCPXML MCP](https://github.com/DareDev256/fcp-mcp-server): source-inspected v0.27.2 and now **direct-MCP host-verified** on the user's Intel Mac against synthetic timelines, but **not yet Open Interpreter client-verified or native Final Cut GUI-verified**. FCP_PROJECTS_DIRS restricts reads through the server API; legacy FCP_PROJECTS_DIR only controls listing. These variables must BOTH point to a disposable root; an MCP tool allowlist is not a full OS sandbox.

**Repository state:** this PR adds an explicitly disabled FCPXML entry to .openinterpreter/config.toml (primary), beside a separately disabled .codex/config.toml entry (fallback). Neither file authorizes private media reads or installs the server.

## Observed first direct MCP smoke attempt — 2026-10-22

Amar ran the pinned `tools/fcp_host_smoke.py` on the Intel Mac. The installed Final Cut Pro FCPXML 1.13 DTD was found and both 60 fps synthetic fixtures passed `xmllint` before `uvx` was started. The attempted MCP handshake **FAILED** at stage `verify_mcp`: `MCP exited before replying`. No direct MCP tool reply, Interpreter MCP registration/handshake, or native Final Cut control was verified. The relevant stdout report stores `status=failed`, `native_final_cut_operated=false`, and `interpreter_mcp_client_verified=false`.

**2026-10-22 root cause confirmed from the Mac's private stderr:** `uvx` resolved `cryptography==50.0.2` and attempted to build its source distribution, but `openssl-sys` could not locate development OpenSSL. `cryptography` 49.0.0 removed Intel macOS wheels, so this is a dependency compatibility issue, **not** a Final Cut app failure or an MCP protocol failure. `cryptography==46.0.5` still ships a CPython 3.11 `macosx_10_9_universal2` wheel. The FCP pilot now adds `--with cryptography==46.0.5` and `--no-build` to the `uvx` command in `tools/fcp_host_smoke.py`, `.openinterpreter/config.toml` (primary) and `.codex/config.toml` (fallback). The `--no-build` flag fails closed rather than compiling unknown source packages. Sources: [cryptography changelog](https://cryptography.io/en/50.0.2/changelog/), [cryptography 46.0.5 wheels](https://pypi.org/project/cryptography/46.0.5/) and [uv tool guide](https://docs.astral.sh/uv/concepts/tools/).

A subsequent diagnostic improvement on this branch saves the **pre-cleanup child exit code**, retained stderr length and SHA-256 in `receipt.json` without printing raw stderr. A dedicated `macos-15-intel` GitHub Actions [run 39852393294](https://github.com/TeamRovor/rovor-video-engine/actions/runs/39852393294) **PASSED** on a genuine Intel x86_64 GitHub runner (2026-10-22). It installed wheels without source compilation, started MCP server v0.27.2, inspected synthetic 1080p60 landscape/portrait timelines, and refused a synthetic outside-root path. The CI result deliberately reports `final_cut_operated=false` and `interpreter_connected=false`. **The user's own Mac subsequently passed the patched tester (see local direct-MCP proof below).** The GitHub-only diagnostic unit test suite passed **9/9** on commit `d9ba5f7`; that is a synthetic transport test, **not** a Mac MCP pass. Do not claim that Final Cut has been connected until an actual inspect response and rejected out-of-root read have been captured.

## Proven on user's Intel Mac — 2026-10-22 (local direct MCP)

The operator executed the **patched** pinned smoke script and provided the full stdout receipt. Latest PRIVATE Mac evidence folder: `~/Documents/Rovor/fcp-mcp-check-20261022-155558`.

- Status: `passed_direct_mcp`, stage `complete`; MCP server name `fcp-mcp-server`, version `0.27.2`
- Installed Apple FCPXML 1.13 DTD copied and synthetic fixtures validated locally
- Real MCP initialize, tools/list and `inspect:analyze_timeline` succeeded for `1920x1080 @ 60fps` landscape and `1080x1920 @ 60fps` portrait
- An explicit synthetic sentinel outside `FCP_PROJECTS_DIRS` was refused with `Validation error: File path escapes the allowed roots`
- `native_final_cut_operated=false` and `interpreter_mcp_client_verified=false`; both are STILL pending

**Next stage is prepared in code, NOT executed on the user's Mac:** `tools/fcp_interpreter_stage.py` validates the prior passing receipt and its two real fixture files, then generates a NEW private one-use Open Interpreter project. Only `inspect` is enabled; the sandbox/approval mode is read-only/on-request and MCP is marked required. The new root has its own synthetic files and outside-root sentinel; it contains no private media or provider settings. No model process or Final Cut app is invoked during staging.

Use a fresh new output path and the actual proof directory:

~~~sh
python3 tools/fcp_interpreter_stage.py \
  --evidence "$HOME/Documents/Rovor/fcp-mcp-check-20261022-155558" \
  --output "$HOME/Documents/Rovor/fcp-interpreter-stage-$(date +%Y%m%d-%H%M%S)"
~~~

The stage script prints its PRIVATE project path, but **do not run bare `interpreter mcp list`** in an untrusted stage; that was the observed failure. Run `tools/fcp_interpreter_registration.py --stage <existing-stage-root>` to prove the ephemeral CLI registration and get the generated wrapper. Invoking the wrapper's `mcp list` or `mcp get` still verifies **registration only**, NOT an MCP handshake. Operator can then opt into a single foreground `interpreter` session, inspect `/debug-config` and `/mcp`, approve one real `inspect` call for each synthetic file and a rejected outside-root sentinel. Preserve local reports as private evidence. The stage does not invoke a model or authorize spending automatically.

## Observed failure: project-local MCP config was ignored (2026-10-22)

The user's first staged project completed successfully, then **bare** `interpreter mcp list` printed `No MCP servers configured yet` and `interpreter mcp get fcpxml` printed `No MCP server named 'fcpxml' found`. No model was invoked. This is a **failed Open Interpreter registration**, NOT failure of the already confirmed direct FCP MCP transport.

**Actual root cause in pinned Open Interpreter v0.0.56's loader:** project-local `.openinterpreter/config.toml` is loaded as a *disabled* layer for an untrusted project. This one-use folder is outside an explicitly trusted project. The CLI source `codex-rs/config/src/loader/mod.rs` says project-local configs are disabled if untrusted; `codex-rs/cli/src/mcp_cmd.rs` obtains the effective config, not all disabled layers. The old script wrongly assumed the directory alone was sufficient.

**Corrected no-global-change gate:** `tools/fcp_interpreter_registration.py --stage <existing-stage-root>` validates the previous stage, supplies the exact restricted FCP MCP entry using Open Interpreter's global per-run `-c` TOML inline-table override, and checks the actual `interpreter mcp list --json` response. It refuses empty/mismatched entries, wrong paths, changed stage files, disabled servers and failed CLI responses. It creates an owner-only `run-interpreter-fcp.sh` ONLY after successful registration. This neither writes `~/.openinterpreter/config.toml` nor adds any permanent trust or starts a model. The wrapper must be used for subsequent TUI registration, because bare `interpreter` still won't consume the project-local layer when untrusted.

**Actual Open Interpreter v0.0.56 integration CI PASSED:** [Intel macOS run 39855908281](https://github.com/TeamRovor/rovor-video-engine/actions/runs/39855908281) downloaded the pinned release, loaded the ephemeral `-c` MCP entry while the project was untrusted, and exercised the complete synthetic stage → `fcp_interpreter_registration.verify_cli()` path, including creation of a private wrapper. Zero model inference, no MCP server transport, no native Final Cut. The same separate diagnostic/test suite passed **25/25** offline tests. **Mac local registration is still pending**; do not mark Jane connected from CI alone.

**Confirmed on user's Intel Mac:** `tools/fcp_interpreter_registration.py --stage ~/Documents/Rovor/fcp-interpreter-stage-20261022-160459` returned `passed_interpreter_registration_only`, MCP server `fcpxml`, tool allowlist `["inspect"]`, private launcher `.../project/run-interpreter-fcp.sh`, and `cli_registration_sha256=0b1b29338af9e74131b4142a56d311d7cd80355b0401651d7f9e412b711ebe2d`. No model or MCP server launched. This is **real Mac CLI registration proof** and should not be re-run unnecessarily.

**CI proof of Open Interpreter MCP client (not user's Mac yet):** `tools/fcp_interpreter_appserver_smoke.py` calls the actual `interpreter app-server` JSON-RPC (`initialize`, ephemeral `thread/start`, `mcpServerStatus/list`, `mcpServer/tool/call`) WITHOUT `turn/start` or any model. It calls the pinned real `fcp-mcp-server==0.27.2` `inspect` tool against two 60fps synthetic timelines and verifies the outside-root sentinel is rejected. [Intel macOS CI run 39858034351](https://github.com/TeamRovor/rovor-video-engine/actions/runs/39858034351) passed, with `open_interpreter_connected=true`, `model_turn_started=false` and `native_final_cut_operated=false`. This is a genuine MCP tool call **through Open Interpreter**, not direct MCP masquerading as a client. The user's Mac still needs this single app-server proof; do not claim Jane's host-level editing or FCP GUI access.

**Do not mistake registration for a handshake:** `mcp list` reads effective configuration but does not initialize the third-party server. Only an actual Interpreter-enabled MCP tool response proves the subsequent gate. Running the wrapper in foreground and invoking a model/tool remains explicitly opt-in. The registered tool list is restricted to `inspect`, with individual approval prompts, on a new synthetic folder. This is application-level scoping, not proof of OS-level filesystem confinement.

## First read-only host checks (normal macOS Terminal)

Use a clean local checkout/worktree containing PR #37; preserve changes in the existing interpreter pilot and do not update dirty branches blindly.

~~~sh
cd "$HOME/Documents/Rovor/rovor-fcp-pilot" || exit 1
git status --short
sh integrations/final-cut-pro/preflight-mac.sh
interpreter --version
interpreter mcp list
interpreter mcp get fcpxml
~~~

These are inspections, not proof of an MCP handshake. The fcpxml MCP must still be disabled. If the CLI does not recognize a command, capture interpreter --help/version, and report the mismatch instead of trying guessed flags.

Start foreground:

~~~sh
interpreter
~~~

INSIDE its TUI, inspect /debug-config, /mcp and /agent. Verify project config, Walter/Jane roles and that FCPXML remains disabled. If daemon mismatch warning appears, it does not alone prove foreground execution is broken or operational. Ask ONE small read-only question with the configured provider; avoid spawning all specialists on a low quota. Keep model/billing unchanged.

## Manual opt-in MCP connection (requires Mac operator approval)

1. Review upstream code and the pinned external package before download or installation; verify installed versions of Python/uvx/FCP.
2. Create a NEW EMPTY directory such as ~/Movies/ROVOR-FCP-Sandbox with only synthetic demo media/XML. Do not reuse a personal folder or import original Evan assets, client files or 4:23 narration.
3. Edit ONLY the local copy of .openinterpreter/config.toml: replace BOTH intentionally invalid FCP path placeholders with the SAME absolute demo folder; retain FCP_PROJECTS_DIRS, FCP_MCP_AUTOPUSH=0, required=false and the inspect/diagnose/view tool allowlist. After explicit authorization, set enabled=true.
4. Restart local Open Interpreter foreground; use interpreter mcp list and /mcp to confirm the actual registered tool list/handshake. Call a real read-only inspect on the synthetic XML. Try a safe known XML path outside the root; it MUST be rejected. Do NOT search a private disk for an outside file. Capture versions, observed result, hashes and errors.
5. Only after review, approve one generated/edited disposable XML copy; inspect it and separately authorize importing into a new test Final Cut library. Check real video exports using normal playback/ffprobe when available. Never modify approved projects.
6. Rollback: stop the agent, set enabled=false, restart; leave original libraries intact. Never commit local paths/provider credentials/permissions to GitHub.

Codex can be used as a fallback for the SAME scoped read-only experiment only if Interpreter is demonstrably blocked. Mark results Codex-only rather than claiming Open Interpreter works. Do not abandon Open Interpreter.

## Turning Jane into an actual ghost employee

The ghost workforce has demonstrated a separate **read-only Jane research** queue job on the user's Mac (one executed, one succeeded, with a receipt and source work). That research job does NOT demonstrate Final Cut MCP use, native editing, GUI control, email/social publishing, or continuous unattended employment. The registry has no enabled Final Cut edit adapter, and all durable local execution must remain approval-gated.

After a verified foreground connection, add a separately claimed **Interpreter research adapter** that runs ONE authorized read-only task via the documented interpreter exec interface and returns a file/receipt with sources, exact tool/model/version, time/budget, input and output hashes. Validate cancellation, crash restart, duplicate submissions, unattended approval behavior and quota exhaustion before connecting to a scheduler. Next add a supervised FCP read/analysis adapter; later add reversible timeline edits with explicit approvals and normal-speed video QA. Keep software install, personal file access, social posting, emails, spending and original project mutation approval-gated.

A role configuration + MCP declaration is not a scheduled worker, and the present GitHub-only work does NOT imply the cloud chat can operate the Mac or that any local FCP work has run.

## First research request to Walter after host verification

"Read current ROVOR AGENTS.md/WORK.md and task queue, then Jane's RESEARCH-PACKET.md. Jane should study the latest official Final Cut Pro documentation and how to assemble professional YouTube/Reels from real motion, original narration, music and SFX. Mike should inventory installed FCP, uvx, FFmpeg and the real available MCP tools. Claim a non-overlapping bounded task, save sources and actual test receipts, and stop if provider/runtime/permission evidence is missing. Do not install software, read private libraries, generate paid inference, send email or post without authorization."
