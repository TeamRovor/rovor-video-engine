# ROVOR Blender MCP — trusted local Codex connection

**Stage: repository configuration prepared, NOT connected to either laptop.** This is a new **Blender capability** alongside ROVOR's non-Moho video renderer and separate Moho track. No original Evan assets, Moho rig, private MP3s, credentials or existing render branches are touched.

## Which upstream?

The maintained open-source repository is [ahujasid/mcp-for-blender](https://github.com/ahujasid/mcp-for-blender) (MIT license, third-party; not the Blender Foundation). On **September 16, 2026**, the maintainer [renamed the package](https://github.com/ahujasid/mcp-for-blender/issues/366) from `blender-mcp` to **`mcp-for-blender`**. The user-provided `uvx blender-mcp install-addon` remains supported via a compatibility wrapper. **New installations should use `uvx mcp-for-blender install-addon`.** Do not vendor/copy upstream source into ROVOR when a client-managed package reference is sufficient.

## What is configured in GitHub (already committed)

- [`.codex/config.toml`](../../.codex/config.toml) supplies the project's local Codex MCP server:
  `uvx --python 3.11 mcp-for-blender` with `BLENDER_HOST=127.0.0.1`, `BLENDER_PORT=9876`, `BLENDER_MCP_SAFE_MODE=1` and `UV_PYTHON_PREFERENCE=only-managed`.
- [`mcp.json.example`](mcp.json.example) supplies matching `mcpServers` JSON for an MCP client that expects that shape, such as a compatible Cursor or Claude Desktop configuration. **It is a template, not a global system config.** VS Code may instead expect the `servers` schema; do not paste the example into unrelated JSON formats without checking.
- [`tools/blender_mcp_preflight.py`](../../tools/blender_mcp_preflight.py) is a read-only, stdlib-only local config validation. Optional `--socket-check` tests for a **local TCP listener only**, not an MCP handshake.
- [`tests/test_blender_mcp_preflight.py`](../../tests/test_blender_mcp_preflight.py) checks the two configurations agree, that unsafe host/commands/settings are rejected and that the preflight does not run Blender.

**Critical distinction:** GitHub can commit configuration and source, but this ChatGPT cloud conversation does not gain remote access to an application simply because the configuration exists. Codex must run **on the computer where Blender runs** and trust/open the cloned ROVOR repo; then it can start the local MCP process and use the available tools. A cloud browser/ChatGPT web session cannot reach this `localhost` automatically.

## Mac (Amar) — local actions required

Run in Terminal **on the Mac with Blender installed**:

```sh
# If uv / uvx is not already installed:
brew install uv

uvx mcp-for-blender install-addon
uvx mcp-for-blender addon-paths

# From the local checkout containing this merged config:
cd /path/to/rovor-video-engine
python3 tools/blender_mcp_preflight.py
python3 -m unittest -v tests.test_blender_mcp_preflight
```

In Blender, open **Edit → Preferences → Add-ons**, enable **Interface: MCP for Blender** (restart Blender if required), then in the **3D Viewport**, press **N**, open the **MCP for Blender** tab and select **Start MCP Server / Connect** (wording depends on add-on version). Keep it on the loopback default port `9876`.

From the **same local cloned ROVOR project**, open a **trusted** Codex session. Codex only loads project-level `.codex/config.toml` for trusted repositories. Check `codex mcp list` and the in-session MCP tools; then try a read-only **get_scene_info** action. Codex CLI and desktop project-aware usage can load the project TOML; this does not modify the ChatGPT web developer settings.

```sh
cd /path/to/rovor-video-engine
python3 tools/blender_mcp_preflight.py --socket-check
codex mcp list
codex
```

If the terminal says `uvx: command not found`, verify `command -v uvx`. A GUI-launched client may not inherit your shell PATH; configure **that machine's local Codex user config** using uvx's real absolute path if needed. Do not hardcode your Mac executable paths in the shared repository.

## Windows (Evan) — independent endpoint

Each computer has its own Blender process, `uvx`, MCP server, and socket. A GitHub-connected ChatGPT session on one machine is not automatically connected to the other.

From **PowerShell on the actual Windows laptop** (only if Blender and Codex are installed and the owner wants the add-on):

```powershell
# If uv is missing, use uv's official installer after reviewing it:
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

uvx mcp-for-blender install-addon
uvx mcp-for-blender addon-paths

cd C:\path\to\rovor-video-engine
py -3 tools/blender_mcp_preflight.py
py -3 -m unittest -v tests.test_blender_mcp_preflight
codex mcp list
```

Enable/add the plug-in in Windows Blender, start the Blender MCP sidebar server, then launch Codex from that local checkout. The project TOML works without shared personal Windows paths. If a GUI cannot find `uvx`, use `where.exe uvx` to locate the executable and configure a local-only override.

## JSON-based MCP client (only if that app actually supports local stdio)

Merge `mcp.json.example` into the client's **own** supported `mcpServers` object; do not replace other servers already configured. The sample is:

```json
{
  "mcpServers": {
    "blender": {
      "command": "uvx",
      "args": ["--python", "3.11", "mcp-for-blender"],
      "env": {
        "BLENDER_HOST": "127.0.0.1",
        "BLENDER_PORT": "9876",
        "BLENDER_MCP_SAFE_MODE": "1",
        "UV_PYTHON_PREFERENCE": "only-managed"
      }
    }
  }
}
```

Do **not** copy this into your ChatGPT web developer settings and assume local execution. Some interfaces cannot launch arbitrary local stdio MCP processes. Codex's real project configuration is the TOML file above; for a user-scoped installation instead, upstream also documents `codex mcp add blender -- uvx mcp-for-blender`, though project-scoped safety/environment details then need to be configured on that machine.

## First genuine acceptance test (no production changes)

1. In a **new disposable .blend project** (never the original Evan character or client project), enable the Blender MCP add-on and start the local server.
2. Confirm `python tools/blender_mcp_preflight.py` succeeds and `--socket-check` reports `tcp_listener: true`. **Listener alone is not Blender authentication or functional readiness.**
3. In local Codex, verify the `blender` MCP tools are offered and request **get_scene_info**. Record tool name, successful response and Blender/add-on/Codex versions.
4. Ask Codex to **create one named cube** in the disposable scene, apply a simple material, and return a screenshot or actual scene inspection. If testing `execute_blender_code`, use a tiny reviewed `bpy` operation confined to this new project. Verify the cube/material in Blender yourself.
5. Only with explicit authorization, save a *new* test `.blend` path and render a low-res still preview; record file existence, dimensions, visual result, time and source version. Restore or remove the disposable project when finished.
6. Mark **local-runtime-verified** only when the tool call, observed scene change, and saved output are all verified on that exact machine. A passing config test is just **configured**, not **connected**.

## Security and reliability boundaries

**Treat this as powerful local code execution.** The server exposes a Blender-Python execution tool. The add-on runs inside your Blender process; source-supplied scripts can potentially read/write files and execute unwanted actions.

- `BLENDER_MCP_SAFE_MODE=1` activates upstream script AST checks; **not a sandbox** or guarantee of harmless behavior. Review code and keep Codex permission prompts enabled.
- Keep the Blender server on **localhost only**. Do not forward `9876`, expose it on the public network, enable remote tunnels, or store tokens in GitHub to force cloud access.
- Use disposable projects and backups, and verify before allowing destructive operations, running third-party scripts, downloading licensed assets or changing deliverable files.
- Only one controlling MCP server instance at a time per Blender process. Stop the server from the Blender sidebar when not in use.
- If the add-on is absent after installation, restart Blender, inspect `addon-paths`, and manually enable the official add-on. If MCP tools appear but cannot connect, first verify Blender's sidebar server and host/port match.
- If `uvx` fails due to conda/pyenv conflicts, the project pins Python 3.11 and uses uv-managed environments. If setup remains broken, capture exact terminal error and installed package versions; do not repeatedly install random GitHub forks.

## Release status and next action

**Current:** code, project TOML, JSON example and preflight are GitHub artifacts. **Not verified:** the local add-on installation, local Codex MCP handshake, arbitrary Python execution inside Blender, rendered preview, or Mac/Windows runtime. GitHub-hosted CI has an independent pre-job failure investigation; do not claim CI passed unless exact tests actually ran.

**Next:** Amar runs the local Mac commands above, enables the add-on in Blender, and executes the first get_scene_info → disposable cube → still-render smoke test through a local trusted Codex session. Evan independently repeats it when his machine is ready. Report exact results into the existing ROVOR task queue; do not create a competing ownership database. More advanced scene scripting follows only after that verified foundation.
