# Jane — Final Cut Pro research and MCP pilot

**State (2026-10-22):** Research references and connection instructions prepared, not installed or verified on Amar's Mac. Walter/Jane are project agent roles, not persistent independently running employees. Final Cut Pro process, version, tool handshake, timeline editing, exports and unattended execution are all **unverified on the Mac**. This connection must not alter the existing Blender MCP, original Evan rig or private narration.

## Jane's job and self-study contract

Jane is ROVOR's video editor and Final Cut Pro research specialist. While assigned an authorized research task, she must read the [software specialist research skill](../../.agents/skills/software-integration-research/SKILL.md), [research packet](RESEARCH-PACKET.md), and canonical [WORK.md](../../WORK.md). She should research official functionality, develop YouTube and Reels editing recipes, compare connection options, verify risks and submit evidence-backed work to the shared GitHub queue. A named role never works in the background merely because it is configured.

Her long-term outcome: take an authorized MP3, existing source-faithful Moho/Blender animation, genuine B-roll, music/SFX and captions; assemble an excellent 60fps video, render both suitable formats and preserve a reversible/editable project. This does not replace proper character animation with still slides.

## Current, inspected connection surfaces

| Path | Evidence | What it can and cannot do |
| --- | --- | --- |
| Apple FCPXML | [Apple developer reference](https://developer.apple.com/documentation/professional-video-applications/fcpxml-reference) | Describe media, metadata and timeline edits for interchange; not a complete replacement for native FCP library/project data |
| Open Document Apple event | [Apple developer guide](https://developer.apple.com/documentation/professional-video-applications/sending-data-programmatically-to-final-cut-pro) | Send a generated .fcpxml to Final Cut using AppleScript; not general live edits or programmatic export |
| Workflow Extensions SDK | [Apple API](https://developer.apple.com/documentation/professional-video-applications/workflow-extensions) | Build a macOS host app and embedded FCP UI extension; does not prove arbitrary timeline mutation |
| FCPXML MCP | [DareDev256/fcp-mcp-server](https://github.com/DareDev256/fcp-mcp-server) | Third-party 15 grouped MCP tools claimed for read, diagnose, edit, preview, generate and delivery; v0.27.2, Python >=3.10 in the Oct 22 inspected pyproject. **Not tested in ROVOR** |
| CommandPost | [CommandPost developer guide](https://github.com/CommandPost/CommandPost-DeveloperGuide) | Optional Lua/AppleScript/CLI accessibility-based automation; different risk profile and additional Mac permissions; compatibility and possible costs need verifying |

**Source provenance:** upstream FCP MCP pyproject.toml Git blob 3d89fa9dc3e521c7e26c7624ed867d8aa772c2d0; server.py blob 7f5640e594f469359301cb12d127c2e5e859a1c1. Base dependencies include mcp>=1.21.1 and defusedxml>=0.7.1. The exact pinned version and signatures must be rechecked when installed; maintainer claims are not user-machine proof.

**Security:** The inspected upstream server.py uses FCP_PROJECTS_DIR for legacy project *listing*, which does **not** by itself restrict file reads. FCP_PROJECTS_DIRS is the additional **read root** allowlist. A pilot must set BOTH to the same disposable absolute folder. The upstream path guards are not a macOS security sandbox. Do not grant broad home/Documents/Desktop access. Never install binary-patching plugins for the first pilot.

## What is registered in the ROVOR codebase

The separate Codex project configuration in .codex/config.toml will have an **explicitly disabled** fcpxml entry after this branch is integrated, with only read-oriented inspect/diagnose/view tools enabled and intentionally invalid placeholder root paths. It must be manually configured on the host and explicitly enabled. This does not install the package, authenticate any provider, load tool permissions into cloud ChatGPT or enable Open Interpreter automatically.

Jane's Open Interpreter role points to this guide. The local interpreter background server on the Intel Mac remains unverified/broken in the last documented check. Use a supported, genuinely running local MCP client such as trusted Codex for the initial test, not an assumed Open Interpreter daemon.

## First Mac research and connection procedure

Run only in the **normal Mac Terminal**, not the in-app ChatGPT text box. This stage reads host facts and makes no software changes:

~~~sh
cd "$HOME/Documents/Rovor/rovor-interpreter-pilot" || exit 1
git status --short
git fetch origin
git log -1 --format='%h %cs %s' origin/main
sw_vers -productVersion
uname -m
if [ -d "/Applications/Final Cut Pro.app" ]; then
  /usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "/Applications/Final Cut Pro.app/Contents/Info.plist"
else
  echo "FCP not found in /Applications; other locations not checked"
fi
command -v uvx || true
command -v codex || true
~~~

Do not pull into a dirty feature branch; preserve the current pilot. Use a clean, authorized worktree on the reviewed branch. Creating the first disposable test folder is an explicit local preparation step, for example **~/Movies/ROVOR-FCP-Sandbox** only if newly created and empty. Do not reuse an existing folder or import private client files.

After checking the third-party source/release and approving its installation:

1. In the clean local ROVOR clone, edit the fcpxml entry in .codex/config.toml. Replace both **/REPLACE_WITH_ABSOLUTE_DISPOSABLE_FCP_PATH** values with the exact same absolute disposable directory. Never commit the machine-specific paths.
2. Confirm FCP_PROJECTS_DIRS and FCP_PROJECTS_DIR match; keep FCP_MCP_AUTOPUSH=0 and the initial enabled_tools limited to inspect, diagnose, view. Only then change enabled to true and start a **trusted local** Codex from that checkout.
3. Confirm **codex mcp list** shows fcpxml, and query actual in-session tool availability. Pin to the reviewed upstream version v0.27.2 using uvx --python 3.11 --from fcp-mcp-server==0.27.2 fcp-mcp-server in the config. Version, runtime and dependency behavior remain untested on this Mac.
4. Run a single read-only **inspect** action on a separately created synthetic/demo FCPXML *inside* the directory. Capture exact output, active version and timestamps. Verify an outside-root read is rejected. Stop if reads escape.
5. Later, **only after explicit permission**, extend one operation at a time to generate/edit/deliver and operate only on copies of demo XML. Import a generated FCPXML into a new disposable Final Cut library; observe the app and permission prompts. Third-party pushing an XML is not proof of editing an existing live timeline.
6. Test a small local demo export, inspect actual decoded video using ffprobe, then view it at normal speed. No real MP3/character media should be used until these gates succeed.

**Rollback:** stop Codex/MCP, set enabled=false, restart Codex and confirm fcpxml is disabled; remove only the newly created demo folder after auditing its contents. Keep original application libraries unchanged.

## ROVOR YouTube and Reels workflow for Jane to learn

**YouTube (landscape):** 1920x1080, 60 fps where supported; original voice first; script/scene storyboard, natural character acting, B-roll shot selection, realistic motion and object contact, audio role separation for music/SFX/dialogue, cohesive pacing, color consistency, chapters, captions, separate review master. Validate full decoded duration/audio and visually approve the whole cut.

**Reels / Shorts (portrait):** 1080x1920, 60 fps where supported; separate 9:16 composition instead of stretched 16:9. Mobile readability, safe caption regions, reframing of Evan and props, transitions that serve the story, concise hook and visual changes, shot-by-shot framing review. Apple documents vertical/square duplicate projects and Smart Conform, but automated reframe still requires review: [Apple guide](https://support.apple.com/en-ph/guide/final-cut-pro/ver8bad7adc6/mac).

**Export and publication:** Apple has Social Platforms export presets and distinct embedded/burned-in captions: [Apple guide](https://support.apple.com/en-euro/guide/final-cut-pro/ver1d41f8374/mac). An exported video is not automatically uploaded; public posting, rights-sensitive licensed music and spending require separate permissions.

**ROVOR acceptance:** Final user-facing review videos at least 30 seconds (shorter internal diagnostics explicitly labeled), 1080p60 landscape and portrait as applicable, original Evan artwork and original speech exactly preserved, accurate lip sync, credible physical animation, no cheap slide-show substitutes. Editing polish cannot repair missing motion in source animation.

## Verified states

- **Research ready:** cited primary/third-party sources, source limitations and study plan. This PR.
- **Configured:** exact local server command and confined test path enabled on a trusted local host.
- **Connected:** successful actual MCP handshake and read-only tool response, with outside-root refusal.
- **Native integrated:** separately authorized import into a new FCP library plus observed result.
- **Editing pilot:** 30+ second visually reviewed source-faithful test video, both output formats, technical QA.
- **Ghost employee:** proven local job runner, durable receipts, bounded execution, cancellation/recovery, safe approvals and scheduled trigger.

Nothing in GitHub alone satisfies the latter five stages.
