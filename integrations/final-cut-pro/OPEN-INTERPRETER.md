# Open Interpreter-first Final Cut Pro connection (Jane)

**Primary local executor: Open Interpreter.** Codex is an optional fallback client, not the ROVOR workforce's primary runtime. Walter coordinates Jane and other existing specialist roles, Open Interpreter supplies local agent sessions/MCP/tool permissions, and GitHub holds source/version/task evidence. None of this alone starts an always-on process or tunnels cloud ChatGPT to the Mac.

## Sources and supported commands (reviewed 2026-10-22)

- [Open Interpreter MCP](https://github.com/openinterpreter/openinterpreter/blob/main/docs/mcp.md): project or user configurations under [mcp_servers.*], CLI commands interpreter mcp list/get/add/remove, in-TUI /mcp and /mcp verbose. Supports enabled_tools, default_tools_approval_mode, enabled and required. A registered server is NOT a connected server.
- [Configuration](https://github.com/openinterpreter/openinterpreter/blob/main/docs/config.md): trusted project settings in .openinterpreter/config.toml, a DIFFERENT file from .codex/config.toml; /debug-config shows loaded layers.
- [CLI reference](https://github.com/openinterpreter/openinterpreter/blob/main/docs/cli-reference.md): interpreter foreground, interpreter exec for one-off noninteractive tasks, interpreter mcp, interpreter mcp-server, and interactive sessions. Do not assume local command works before running it.
- [Daemon documentation](https://www.openinterpreter.com/docs/terminal/daemon): normal foreground operation does not require a daemon; shared background daemon is optional. But the user's Intel Mac v0.0.56 had a persistent package/platform mismatch on daemon start. Foreground agent/skills/MCP still need separate proof.
- [Third-party FCPXML MCP](https://github.com/DareDev256/fcp-mcp-server): source-inspected v0.27.2, not installed or ROVOR host-verified. FCP_PROJECTS_DIRS restricts file reads; legacy FCP_PROJECTS_DIR only controls listing. These environment variables must BOTH point to a disposable root.

**Repository state:** this PR adds an explicitly disabled FCPXML entry to .openinterpreter/config.toml (primary), beside a separately disabled .codex/config.toml entry (fallback). Neither file authorizes private media reads or installs the server.

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

The current ghost worker PRs #32-34 implement SQLite receipts, bounded polling and optional launch scheduling, but ONLY read-only system.ping and files.inventory job adapters. They do not yet run Interpreter research, Final Cut, Mac GUI or live publishing.

After a verified foreground connection, add a separately claimed **Interpreter research adapter** that runs ONE authorized read-only task via the documented interpreter exec interface and returns a file/receipt with sources, exact tool/model/version, time/budget, input and output hashes. Validate cancellation, crash restart, duplicate submissions, unattended approval behavior and quota exhaustion before connecting to a scheduler. Next add a supervised FCP read/analysis adapter; later add reversible timeline edits with explicit approvals and normal-speed video QA. Keep software install, personal file access, social posting, emails, spending and original project mutation approval-gated.

A role configuration + MCP declaration is not a scheduled worker, and the present GitHub-only work does NOT imply the cloud chat can operate the Mac or that any local FCP work has run.

## First research request to Walter after host verification

"Read current ROVOR AGENTS.md/WORK.md and task queue, then Jane's RESEARCH-PACKET.md. Jane should study the latest official Final Cut Pro documentation and how to assemble professional YouTube/Reels from real motion, original narration, music and SFX. Mike should inventory installed FCP, uvx, FFmpeg and the real available MCP tools. Claim a non-overlapping bounded task, save sources and actual test receipts, and stop if provider/runtime/permission evidence is missing. Do not install software, read private libraries, generate paid inference, send email or post without authorization."
